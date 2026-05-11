"""Tests that verify which S3 bucket each build type is stored in, and that
the /builds/ endpoint routes to the correct backend depending on User-Agent
and HTTP method.

Bucket routing based on build name:
  *:staging-*   → artifacts-staging
  *:promoted-*  → artifacts-promoted
  anything else → artifacts-prolonged

Uploads via the artifacts API only accept staging build names (nginx regex
enforces this).  For promoted/prolonged builds we insert objects directly via
the S3 client and verify the artifacts download API can still retrieve them.

/builds/ backend routing:
  GET  + non-Mozilla UA  → /redirect/ → 302 presigned S3 URL
  GET  + Mozilla UA      → /download/ → 200 proxied
  HEAD + any UA          → /download/ → 200 proxied (HEAD is always direct)
"""

import pytest

from constants import STAGING_BUILD, PROMOTED_BUILD, PROLONGED_BUILD


def test_staging_upload_stored_in_staging_bucket(
    session, artifacts_url, s3_client
):
    """Upload via /upload/ lands in artifacts-staging."""
    resp = session.put(
        f'{artifacts_url}/upload/{STAGING_BUILD}/file.txt',
        data=b'hello',
    )
    assert resp.status_code == 200

    # Verify object is present in the staging bucket directly via S3
    objs = s3_client.list_objects(Bucket='artifacts-staging')
    keys = [o['Key'] for o in objs.get('Contents', [])]
    assert f'{STAGING_BUILD}/file.txt' in keys

    # Must NOT be in the other buckets
    for bucket in ('artifacts-promoted', 'artifacts-prolonged'):
        objs = s3_client.list_objects(Bucket=bucket)
        keys = [o['Key'] for o in objs.get('Contents', [])]
        assert f'{STAGING_BUILD}/file.txt' not in keys


def test_promoted_build_downloadable_from_promoted_bucket(
    session, artifacts_url, s3_client
):
    """Objects placed directly in artifacts-promoted are retrievable via /download/."""
    key = f'{PROMOTED_BUILD}/release.txt'
    s3_client.put_object(Bucket='artifacts-promoted', Key=key, Body=b'release')

    resp = session.get(
        f'{artifacts_url}/download/{PROMOTED_BUILD}/release.txt',
        headers={'ForceCacheUpdate': 'yes'},
    )
    assert resp.status_code == 200
    assert resp.content == b'release'


def test_prolonged_build_downloadable_from_prolonged_bucket(
    session, artifacts_url, s3_client
):
    """Objects placed directly in artifacts-prolonged are retrievable via /download/."""
    key = f'{PROLONGED_BUILD}/notes.txt'
    s3_client.put_object(Bucket='artifacts-prolonged', Key=key, Body=b'notes')

    resp = session.get(
        f'{artifacts_url}/download/{PROLONGED_BUILD}/notes.txt',
        headers={'ForceCacheUpdate': 'yes'},
    )
    assert resp.status_code == 200
    assert resp.content == b'notes'


def test_builds_cli_ua_redirects_to_presigned_url(upload_file, session, artifacts_url):
    """GET /builds/ with a non-Mozilla UA is rewritten to /redirect/ → 302."""
    upload_file(STAGING_BUILD, 'file.txt')
    resp = session.get(
        f'{artifacts_url}/builds/{STAGING_BUILD}/file.txt',
        headers={'User-Agent': 'curl/7.83.1'},
        allow_redirects=False,
    )
    assert resp.status_code == 302


def test_builds_browser_ua_proxied_directly(upload_file, session, artifacts_url):
    """GET /builds/ with a Mozilla UA is rewritten to /download/ → 200 proxied.

    The response body must be the file content, not an HTML directory listing.
    """
    data = b'browser-proxied content'
    upload_file(STAGING_BUILD, 'file.txt', data=data)
    resp = session.get(
        f'{artifacts_url}/builds/{STAGING_BUILD}/file.txt',
        headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'},
        allow_redirects=False,
    )
    assert resp.status_code == 200
    assert resp.content == data


def test_builds_head_always_proxied_regardless_of_ua(upload_file, session, artifacts_url):
    """HEAD /builds/ with a non-Mozilla UA is still rewritten to /download/ → 200."""
    upload_file(STAGING_BUILD, 'file.txt')
    resp = session.head(
        f'{artifacts_url}/builds/{STAGING_BUILD}/file.txt',
        headers={'User-Agent': 'curl/7.83.1'},
        allow_redirects=False,
    )
    assert resp.status_code == 200


def test_staging_build_not_visible_from_promoted_bucket(
    session, artifacts_url, s3_client
):
    """A staging build name is not found when querying via the promoted bucket key."""
    # Upload to staging via the API
    session.put(
        f'{artifacts_url}/upload/{STAGING_BUILD}/file.txt',
        data=b'staging',
    )

    # The promoted bucket must still be empty
    objs = s3_client.list_objects(Bucket='artifacts-promoted')
    assert objs.get('Contents') is None
