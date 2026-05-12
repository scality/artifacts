"""Shared helpers for multipart upload test suites."""

import re


def multipart_initiate(session, artifacts_url, build, path):
    """POST /upload-multipart/initiate/{build}/{path} → uploadId."""
    resp = session.post(
        f'{artifacts_url}/upload-multipart/initiate/{build}/{path}',
        headers={'Content-Length': '0'},
    )
    assert resp.status_code == 200, f'initiate failed: {resp.status_code} {resp.text}'
    match = re.search(r'<UploadId>([^<]+)</UploadId>', resp.text)
    assert match, f'No UploadId in initiate response: {resp.text}'
    return match.group(1)


def multipart_complete(session, artifacts_url, build, path, upload_id, parts):
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
