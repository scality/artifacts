"""Tests for the presigned upload endpoints.

/presign-upload/<build>/<path>         → presigned S3 PUT URL for a single file
/presign-upload-part/<build>/<path>    → presigned S3 PUT URL for one multipart part

The presigned URL is returned as plain text (200).  The client then PUTs the
file body (or part body) directly to S3 without going through nginx.
"""

import hashlib
import re

import requests

from constants import STAGING_BUILD, PROMOTED_BUILD


# ---------------------------------------------------------------------------
# Helpers shared with multipart flow
# ---------------------------------------------------------------------------

def _initiate(session, artifacts_url, build, path):
    resp = session.post(
        f'{artifacts_url}/upload-multipart/initiate/{build}/{path}',
        headers={'Content-Length': '0'},
    )
    assert resp.status_code == 200, f'initiate failed: {resp.status_code} {resp.text}'
    match = re.search(r'<UploadId>([^<]+)</UploadId>', resp.text)
    assert match, f'No UploadId in response: {resp.text}'
    return match.group(1)


def _complete(session, artifacts_url, build, path, upload_id, parts):
    xml_parts = ''.join(
        f'<Part><PartNumber>{pn}</PartNumber><ETag>{etag}</ETag></Part>'
        for pn, etag in sorted(parts)
    )
    xml_body = f'<CompleteMultipartUpload>{xml_parts}</CompleteMultipartUpload>'
    resp = session.post(
        f'{artifacts_url}/upload-multipart/complete/{build}/{path}',
        params={'uploadId': upload_id},
        data=xml_body.encode(),
        headers={'Content-Type': 'application/xml'},
    )
    assert resp.status_code == 200, f'complete failed: {resp.status_code} {resp.text}'
    return resp


# ---------------------------------------------------------------------------
# /presign-upload/ — single-file presigned PUT
# ---------------------------------------------------------------------------

def test_presign_upload_returns_url(session, artifacts_url):
    """GET /presign-upload/ returns 200 with a non-empty URL."""
    resp = session.get(f'{artifacts_url}/presign-upload/{STAGING_BUILD}/file.txt')
    assert resp.status_code == 200, f'{resp.status_code} {resp.text}'
    url = resp.text.strip()
    assert url.startswith('http'), f'Expected a URL, got: {url!r}'


def test_presign_upload_file_reachable_after_direct_put(session, artifacts_url):
    """Presigned URL PUT bypasses nginx; the file is then downloadable."""
    data = b'direct-to-s3 content'

    # 1. Get presigned URL from nginx
    presign_resp = session.get(
        f'{artifacts_url}/presign-upload/{STAGING_BUILD}/direct.txt'
    )
    assert presign_resp.status_code == 200
    s3_url = presign_resp.text.strip()

    # 2. PUT directly to S3 (no nginx auth headers)
    put_resp = requests.put(
        s3_url,
        data=data,
        headers={'Content-Length': str(len(data))},
    )
    assert put_resp.status_code == 200, f'S3 PUT failed: {put_resp.status_code} {put_resp.text}'

    # 3. File must be downloadable through nginx
    dl = session.get(
        f'{artifacts_url}/download/{STAGING_BUILD}/direct.txt',
        headers={'ForceCacheUpdate': 'yes'},
    )
    assert dl.status_code == 200
    assert dl.content == data


def test_presign_upload_rejects_non_get(session, artifacts_url):
    """Only GET is allowed on /presign-upload/; other methods return 400."""
    url = f'{artifacts_url}/presign-upload/{STAGING_BUILD}/file.txt'
    assert session.post(url).status_code == 400
    assert session.put(url, data=b'x').status_code == 400


def test_presign_upload_rejects_non_staging_build(session, artifacts_url):
    """Non-staging build names are rejected with 400."""
    resp = session.get(
        f'{artifacts_url}/presign-upload/{PROMOTED_BUILD}/file.txt'
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# /presign-upload-part/ — presigned multipart part PUT
# ---------------------------------------------------------------------------

def test_presign_upload_part_returns_url(session, artifacts_url):
    """GET /presign-upload-part/ with partNumber+uploadId returns a URL."""
    upload_id = _initiate(session, artifacts_url, STAGING_BUILD, 'presign/part-url.bin')
    try:
        resp = session.get(
            f'{artifacts_url}/presign-upload-part/{STAGING_BUILD}/presign/part-url.bin',
            params={'partNumber': 1, 'uploadId': upload_id},
        )
        assert resp.status_code == 200, f'{resp.status_code} {resp.text}'
        url = resp.text.strip()
        assert url.startswith('http'), f'Expected a URL, got: {url!r}'
    finally:
        session.delete(
            f'{artifacts_url}/upload-multipart/abort/{STAGING_BUILD}/presign/part-url.bin',
            params={'uploadId': upload_id},
        )


def test_presign_multipart_full_round_trip(session, artifacts_url):
    """Initiate via nginx, upload parts directly to S3, complete via nginx."""
    build = STAGING_BUILD
    path = 'presign/multipart.bin'
    part1 = b'A' * (6 * 1024 * 1024)   # 6 MB  (S3 minimum non-last part)
    part2 = b'B' * (1 * 1024 * 1024)   # 1 MB  (last part, may be smaller)

    # 1. Initiate through nginx
    upload_id = _initiate(session, artifacts_url, build, path)

    etags = []
    try:
        for part_number, data in [(1, part1), (2, part2)]:
            # 2. Get presigned part URL from nginx
            presign_resp = session.get(
                f'{artifacts_url}/presign-upload-part/{build}/{path}',
                params={'partNumber': part_number, 'uploadId': upload_id},
            )
            assert presign_resp.status_code == 200, \
                f'presign-part {part_number} failed: {presign_resp.status_code} {presign_resp.text}'
            s3_url = presign_resp.text.strip()

            # 3. PUT part directly to S3
            put_resp = requests.put(
                s3_url,
                data=data,
                headers={'Content-Length': str(len(data))},
            )
            assert put_resp.status_code == 200, \
                f'S3 part {part_number} PUT failed: {put_resp.status_code} {put_resp.text}'
            etag = put_resp.headers.get('ETag', '')
            assert etag, f'No ETag for part {part_number}'
            etags.append((part_number, etag))
    except Exception:
        session.delete(
            f'{artifacts_url}/upload-multipart/abort/{build}/{path}',
            params={'uploadId': upload_id},
        )
        raise

    # 4. Complete through nginx
    _complete(session, artifacts_url, build, path, upload_id, etags)

    # 5. Verify the assembled object
    dl = session.get(
        f'{artifacts_url}/download/{build}/{path}',
        headers={'ForceCacheUpdate': 'yes'},
    )
    assert dl.status_code == 200
    expected = part1 + part2
    assert len(dl.content) == len(expected)
    assert hashlib.sha256(dl.content).hexdigest() == hashlib.sha256(expected).hexdigest()


def test_presign_upload_part_rejects_non_staging(session, artifacts_url):
    """Non-staging build names are rejected on /presign-upload-part/ too."""
    resp = session.get(
        f'{artifacts_url}/presign-upload-part/{PROMOTED_BUILD}/file.bin',
        params={'partNumber': 1, 'uploadId': 'fake-id'},
    )
    assert resp.status_code == 400
