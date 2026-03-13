"""Tests for /last_success/, /last_failure/, and /latest/ endpoints.

These endpoints scan all builds matching a prefix and find the most-recent
one whose .final_status matches the expected value (SUCCESSFUL / FAILED / any).
"""

import pytest

from constants import STAGING_BUILD


# Three staging builds that share a common prefix and sort A < B < C.
# The suffix must be digits to satisfy the upload regex:
#   staging-<hash>.<branch>.<number>(.<number>)?
BUILD_A = 'githost:owner:repo:staging-8e50acc6a1.pre-merge.28.1'
BUILD_B = 'githost:owner:repo:staging-8e50acc6a1.pre-merge.28.2'
BUILD_C = 'githost:owner:repo:staging-8e50acc6a1.pre-merge.28.3'
# Common prefix shared by all three builds
PREFIX  = 'githost:owner:repo:staging-8e50acc6a1.pre-merge.28.'


def _upload_sentinel(session, artifacts_url, build):
    resp = session.put(f'{artifacts_url}/upload/{build}/.sentinel', data=b'x')
    assert resp.status_code == 200


def _set_status(session, artifacts_url, build, status):
    resp = session.put(
        f'{artifacts_url}/upload/{build}/.final_status',
        data=status.encode(),
    )
    assert resp.status_code == 200
    # Flush proxy cache
    session.get(
        f'{artifacts_url}/download/{build}/.final_status',
        headers={'ForceCacheUpdate': 'yes'},
    )


# ---------------------------------------------------------------------------
# /last_success/
# ---------------------------------------------------------------------------

def test_last_success_redirects_to_latest_successful_build(
    session, artifacts_url
):
    _upload_sentinel(session, artifacts_url, BUILD_A)
    _upload_sentinel(session, artifacts_url, BUILD_B)
    _set_status(session, artifacts_url, BUILD_A, 'SUCCESSFUL')
    _set_status(session, artifacts_url, BUILD_B, 'SUCCESSFUL')

    resp = session.get(
        f'{artifacts_url}/last_success/{PREFIX}',
        allow_redirects=False,
    )
    assert resp.status_code == 302
    # BUILD_B sorts after BUILD_A → latest successful is BUILD_B
    assert resp.headers['Location'] == f'/download/{BUILD_B}/'


def test_last_success_head_returns_redirect(session, artifacts_url):
    _upload_sentinel(session, artifacts_url, BUILD_A)
    _set_status(session, artifacts_url, BUILD_A, 'SUCCESSFUL')

    resp = session.head(
        f'{artifacts_url}/last_success/{PREFIX}',
        allow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers['Location'] == f'/download/{BUILD_A}/'


def test_last_success_follows_redirect_to_listing(session, artifacts_url):
    _upload_sentinel(session, artifacts_url, BUILD_A)
    _set_status(session, artifacts_url, BUILD_A, 'SUCCESSFUL')

    resp = session.get(f'{artifacts_url}/last_success/{PREFIX}')
    assert resp.status_code == 200


def test_last_success_returns_404_when_no_successful_build(session, artifacts_url):
    _upload_sentinel(session, artifacts_url, BUILD_A)
    _set_status(session, artifacts_url, BUILD_A, 'FAILED')

    resp = session.get(
        f'{artifacts_url}/last_success/{PREFIX}',
        allow_redirects=False,
    )
    assert resp.status_code == 404


def test_last_success_skips_failed_builds(session, artifacts_url):
    """last_success must skip FAILED builds and return the newest SUCCESSFUL."""
    _upload_sentinel(session, artifacts_url, BUILD_A)
    _upload_sentinel(session, artifacts_url, BUILD_B)
    _upload_sentinel(session, artifacts_url, BUILD_C)
    _set_status(session, artifacts_url, BUILD_A, 'SUCCESSFUL')
    _set_status(session, artifacts_url, BUILD_B, 'SUCCESSFUL')
    _set_status(session, artifacts_url, BUILD_C, 'FAILED')

    resp = session.get(
        f'{artifacts_url}/last_success/{PREFIX}',
        allow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers['Location'] == f'/download/{BUILD_B}/'


# ---------------------------------------------------------------------------
# /last_failure/
# ---------------------------------------------------------------------------

def test_last_failure_redirects_to_latest_failed_build(session, artifacts_url):
    _upload_sentinel(session, artifacts_url, BUILD_A)
    _upload_sentinel(session, artifacts_url, BUILD_B)
    _set_status(session, artifacts_url, BUILD_A, 'FAILED')
    _set_status(session, artifacts_url, BUILD_B, 'FAILED')

    resp = session.get(
        f'{artifacts_url}/last_failure/{PREFIX}',
        allow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers['Location'] == f'/download/{BUILD_B}/'


def test_last_failure_returns_404_when_no_failed_build(session, artifacts_url):
    _upload_sentinel(session, artifacts_url, BUILD_A)
    _set_status(session, artifacts_url, BUILD_A, 'SUCCESSFUL')

    resp = session.get(
        f'{artifacts_url}/last_failure/{PREFIX}',
        allow_redirects=False,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /latest/
# ---------------------------------------------------------------------------

def test_latest_redirects_regardless_of_status(session, artifacts_url):
    """latest/ picks the alphabetically-last build, regardless of .final_status."""
    _upload_sentinel(session, artifacts_url, BUILD_A)
    _upload_sentinel(session, artifacts_url, BUILD_B)
    _set_status(session, artifacts_url, BUILD_A, 'SUCCESSFUL')
    _set_status(session, artifacts_url, BUILD_B, 'FAILED')

    resp = session.get(
        f'{artifacts_url}/latest/{PREFIX}',
        allow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers['Location'] == f'/download/{BUILD_B}/'


def test_latest_returns_404_when_no_builds_match_prefix(session, artifacts_url):
    resp = session.get(
        f'{artifacts_url}/latest/no_such_prefix',
        allow_redirects=False,
    )
    assert resp.status_code == 404


def test_latest_with_no_final_status_still_redirects(session, artifacts_url):
    """latest/ does not require a .final_status file at all."""
    _upload_sentinel(session, artifacts_url, BUILD_A)

    resp = session.get(
        f'{artifacts_url}/latest/{PREFIX}',
        allow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers['Location'] == f'/download/{BUILD_A}/'
