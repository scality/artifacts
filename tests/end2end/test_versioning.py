"""Tests for the /version/ (object snapshotting) endpoint."""

import pytest

from constants import STAGING_BUILD


def test_version_object(session, artifacts_url, upload_file):
    """Versioning a file stores it under .ARTIFACTS_BEFORE/<version>/."""
    upload_file(STAGING_BUILD, '.final_status', b'SUCCESSFUL')

    resp = session.get(f'{artifacts_url}/version/42/{STAGING_BUILD}/.final_status')
    assert resp.status_code == 200

    dl = session.get(
        f'{artifacts_url}/download/{STAGING_BUILD}/.ARTIFACTS_BEFORE/42/.final_status'
    )
    assert dl.status_code == 200
    assert dl.content == b'SUCCESSFUL'


def test_version_object_with_spaces_in_path(session, artifacts_url, upload_file):
    """Objects whose names contain spaces are versioned correctly."""
    upload_file(STAGING_BUILD, 'object with space chars', b'SUCCESSFUL')

    resp = session.get(
        f'{artifacts_url}/version/42/{STAGING_BUILD}/object with space chars'
    )
    assert resp.status_code == 200

    dl = session.get(
        f'{artifacts_url}/download/{STAGING_BUILD}/.ARTIFACTS_BEFORE/42/object with space chars'
    )
    assert dl.status_code == 200
    assert dl.content == b'SUCCESSFUL'
