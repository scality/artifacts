"""Tests for the multipart upload endpoints."""

import hashlib
import re
import xml.etree.ElementTree as ET

import pytest

from constants import STAGING_BUILD


def _initiate(session, artifacts_url, build, path):
    """POST /upload-multipart/initiate/{build}/{path} → uploadId."""
    resp = session.post(
        f'{artifacts_url}/upload-multipart/initiate/{build}/{path}',
        headers={'Content-Length': '0'},
    )
    assert resp.status_code == 200, f'initiate failed: {resp.status_code} {resp.text}'
    match = re.search(r'<UploadId>([^<]+)</UploadId>', resp.text)
    assert match, f'No UploadId in initiate response: {resp.text}'
    return match.group(1)


def _upload_part(session, artifacts_url, build, path, upload_id, part_number, data):
    """PUT /upload-multipart/part/{build}/{path}?partNumber=N&uploadId=X → ETag."""
    resp = session.put(
        f'{artifacts_url}/upload-multipart/part/{build}/{path}',
        params={'partNumber': part_number, 'uploadId': upload_id},
        data=data,
        headers={'Content-Length': str(len(data))},
    )
    assert resp.status_code == 200, f'part {part_number} failed: {resp.status_code} {resp.text}'
    etag = resp.headers.get('ETag', '')
    assert etag, f'No ETag returned for part {part_number}'
    return etag


def _complete(session, artifacts_url, build, path, upload_id, parts):
    """POST /upload-multipart/complete/{build}/{path}?uploadId=X with XML body."""
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


def _abort(session, artifacts_url, build, path, upload_id):
    """DELETE /upload-multipart/abort/{build}/{path}?uploadId=X."""
    return session.delete(
        f'{artifacts_url}/upload-multipart/abort/{build}/{path}',
        params={'uploadId': upload_id},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_multipart_upload_single_part(session, artifacts_url):
    """A single-part multipart upload round-trips correctly."""
    build = STAGING_BUILD
    path = 'multipart/single.bin'
    data = b'hello multipart world'

    upload_id = _initiate(session, artifacts_url, build, path)
    etag = _upload_part(session, artifacts_url, build, path, upload_id, 1, data)
    _complete(session, artifacts_url, build, path, upload_id, [(1, etag)])

    dl = session.get(
        f'{artifacts_url}/download/{build}/{path}',
        headers={'ForceCacheUpdate': 'yes'},
    )
    assert dl.status_code == 200
    assert dl.content == data


def test_multipart_upload_multiple_parts(session, artifacts_url):
    """Two-part multipart upload assembles into the correct byte stream."""
    build = STAGING_BUILD
    path = 'multipart/two-parts.bin'
    part1 = b'A' * (6 * 1024 * 1024)  # 6 MB (S3 minimum part size)
    part2 = b'B' * (1 * 1024 * 1024)  # 1 MB last part

    upload_id = _initiate(session, artifacts_url, build, path)
    etag1 = _upload_part(session, artifacts_url, build, path, upload_id, 1, part1)
    etag2 = _upload_part(session, artifacts_url, build, path, upload_id, 2, part2)
    _complete(session, artifacts_url, build, path, upload_id, [(1, etag1), (2, etag2)])

    dl = session.get(
        f'{artifacts_url}/download/{build}/{path}',
        headers={'ForceCacheUpdate': 'yes'},
    )
    assert dl.status_code == 200
    expected = part1 + part2
    assert len(dl.content) == len(expected)
    assert hashlib.sha256(dl.content).hexdigest() == hashlib.sha256(expected).hexdigest()


def test_multipart_upload_abort(session, artifacts_url):
    """Aborting a multipart upload cleans it up; the object is not stored."""
    build = STAGING_BUILD
    path = 'multipart/aborted.bin'
    data = b'this should never land'

    upload_id = _initiate(session, artifacts_url, build, path)
    _upload_part(session, artifacts_url, build, path, upload_id, 1, data)

    abort_resp = _abort(session, artifacts_url, build, path, upload_id)
    assert abort_resp.status_code in (200, 204), \
        f'abort returned: {abort_resp.status_code} {abort_resp.text}'

    # Object must not be present after abort
    dl = session.get(f'{artifacts_url}/download/{build}/{path}')
    assert dl.status_code == 404


def test_multipart_initiate_rejected_for_non_staging(session, artifacts_url):
    """Initiating a multipart upload for a non-staging build is rejected."""
    promoted = 'githost:owner:repo:promoted-abc123.rel.1'
    resp = session.post(
        f'{artifacts_url}/upload-multipart/initiate/{promoted}/file.bin',
        headers={'Content-Length': '0'},
    )
    assert resp.status_code == 400


def test_multipart_upload_parts_out_of_order(session, artifacts_url):
    """Parts submitted out of order are correctly assembled after complete."""
    build = STAGING_BUILD
    path = 'multipart/out-of-order.bin'
    # Non-last parts must meet S3's 5 MB minimum size requirement.
    part1 = b'A' * (6 * 1024 * 1024)
    part2 = b'B' * (1 * 1024 * 1024)  # last part may be smaller

    upload_id = _initiate(session, artifacts_url, build, path)
    # Upload part 2 before part 1 intentionally
    etag2 = _upload_part(session, artifacts_url, build, path, upload_id, 2, part2)
    etag1 = _upload_part(session, artifacts_url, build, path, upload_id, 1, part1)
    # Complete with parts in correct numerical order in the XML
    _complete(session, artifacts_url, build, path, upload_id, [(1, etag1), (2, etag2)])

    dl = session.get(
        f'{artifacts_url}/download/{build}/{path}',
        headers={'ForceCacheUpdate': 'yes'},
    )
    assert dl.status_code == 200
    expected = part1 + part2
    assert hashlib.sha256(dl.content).hexdigest() == hashlib.sha256(expected).hexdigest()
