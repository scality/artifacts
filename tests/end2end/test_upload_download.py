"""Tests for the upload and download paths."""

import hashlib
import os
import tempfile

import pytest

from constants import STAGING_BUILD


def test_upload_then_download_roundtrip(session, artifacts_url):
    """Uploaded content is retrievable byte-for-byte via /download/."""
    data = os.urandom(1024)
    path = 'subdir/myfile.bin'
    build = STAGING_BUILD

    upload = session.put(f'{artifacts_url}/upload/{build}/{path}', data=data)
    assert upload.status_code == 200

    download = session.get(
        f'{artifacts_url}/download/{build}/{path}',
        headers={'ForceCacheUpdate': 'yes'},
    )
    assert download.status_code == 200
    assert download.content == data


def test_upload_then_download_checksum(session, artifacts_url):
    """SHA-256 of uploaded file matches the downloaded file."""
    filename = tempfile.mktemp()
    build = STAGING_BUILD
    path = filename  # reuse the tempfile name as the S3 key

    with open(filename, 'wb') as fd:
        fd.write(os.urandom(1024))

    sha_upload = hashlib.sha256(open(filename, 'rb').read()).hexdigest()

    with open(filename, 'rb') as fd:
        upload = session.put(
            f'{artifacts_url}/upload/{build}{path}',
            data=fd,
        )
    assert upload.status_code == 200

    download = session.get(
        f'{artifacts_url}/download/{build}{path}',
        headers={'ForceCacheUpdate': 'yes'},
    )
    assert download.status_code == 200
    sha_download = hashlib.sha256(download.content).hexdigest()
    assert sha_download == sha_upload

    os.remove(filename)


def test_download_via_redirect_endpoint(session, artifacts_url):
    """The /redirect/ endpoint proxies the object content transparently."""
    data = os.urandom(512)
    build = STAGING_BUILD
    path = 'some/file.txt'

    session.put(f'{artifacts_url}/upload/{build}/{path}', data=data)

    resp = session.get(f'{artifacts_url}/redirect/{build}/{path}')
    assert resp.status_code == 200
    assert resp.content == data


def test_download_via_github_builds_path(session, artifacts_url):
    """The /github/scality/<repo>/builds/ alias resolves to the same object."""
    data = os.urandom(512)
    build = STAGING_BUILD
    path = 'artifact.txt'

    session.put(f'{artifacts_url}/upload/{build}/{path}', data=data)

    resp = session.get(
        f'{artifacts_url}/github/scality/fakerepo/builds/{build}/{path}',
        headers={'ForceCacheUpdate': 'yes'},
    )
    assert resp.status_code == 200
    assert resp.content == data


def test_download_missing_file_returns_404(session, artifacts_url):
    """Downloading a non-existent object returns 404."""
    resp = session.get(f'{artifacts_url}/download/{STAGING_BUILD}/does-not-exist.txt')
    assert resp.status_code == 404


def test_upload_empty_object(session, artifacts_url):
    """Uploading an empty body succeeds (0-byte object)."""
    resp = session.put(
        f'{artifacts_url}/upload/{STAGING_BUILD}/.sentinel',
        data=b'',
    )
    assert resp.status_code == 200


def test_upload_non_staging_build_is_rejected(session, artifacts_url):
    """Uploading to a non-staging build name returns 400."""
    promoted = 'githost:owner:repo:promoted-abc123.rel.1'
    resp = session.put(
        f'{artifacts_url}/upload/{promoted}/file.txt',
        data=b'content',
    )
    assert resp.status_code == 400


def test_upload_object_with_spaces_in_name(session, artifacts_url):
    """Object paths containing spaces are accepted and downloadable."""
    data = b'content with spaces'
    path = 'object with space chars'
    build = STAGING_BUILD

    resp = session.put(f'{artifacts_url}/upload/{build}/{path}', data=data)
    assert resp.status_code == 200

    dl = session.get(f'{artifacts_url}/download/{build}/{path}')
    assert dl.status_code == 200
    assert dl.content == data
