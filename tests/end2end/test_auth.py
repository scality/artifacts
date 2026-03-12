"""Tests for GitHub-based access control and local bot credentials."""

import pytest

from constants import STAGING_BUILD


# ---------------------------------------------------------------------------
# Authenticated users with full upload rights
# ---------------------------------------------------------------------------

def test_authenticated_user_can_upload(session, artifacts_url):
    resp = session.put(
        f'{artifacts_url}/upload/{STAGING_BUILD}/.final_status',
        data=b'SUCCESSFUL',
        headers={'Script-Name': '/foo'},
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Local bot credentials
# ---------------------------------------------------------------------------

def test_bot_credentials_can_download(bot_session, artifacts_url):
    """Bot user (local creds) can hit /download/ — 404 is fine, not 401/403."""
    resp = bot_session.get(f'{artifacts_url}/download/{STAGING_BUILD}')
    # The build doesn't exist, so we get 404 (redirect to trailing slash → 404).
    # What matters is that we are not rejected with 401 or 403.
    assert resp.status_code not in (401, 403)


# ---------------------------------------------------------------------------
# Restricted users (can read, cannot write)
# ---------------------------------------------------------------------------

def test_restricted_user_can_download(restricted_session, artifacts_url):
    """User without upload permission can still browse /download/."""
    resp = restricted_session.get(f'{artifacts_url}/download/{STAGING_BUILD}/')
    # Build doesn't exist → 404; not 401 or 403
    assert resp.status_code == 404


def test_restricted_user_cannot_upload(restricted_session, artifacts_url):
    resp = restricted_session.put(
        f'{artifacts_url}/upload/{STAGING_BUILD}/.final_status',
        data=b'SUCCESSFUL',
    )
    assert resp.status_code == 403


def test_restricted_user_cannot_copy(restricted_session, artifacts_url):
    copy_build = f'copy_of_{STAGING_BUILD}'
    resp = restricted_session.get(
        f'{artifacts_url}/copy/{STAGING_BUILD}/{copy_build}/'
    )
    assert resp.status_code == 403


def test_restricted_user_cannot_add_metadata(restricted_session, artifacts_url):
    resp = restricted_session.get(
        f'{artifacts_url}/add_metadata/fake/args'
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Failing / missing credentials
# ---------------------------------------------------------------------------

def test_failing_github_user_is_forbidden(artifacts_url):
    """A user rejected by the (fake) GitHub API receives 403."""
    s = __import__('requests').Session()
    s.auth = ('username-fail', 'fake-password')
    resp = s.put(
        f'{artifacts_url}/upload/{STAGING_BUILD}/.final_status',
        data=b'SUCCESSFUL',
        headers={'Script-Name': '/foo'},
    )
    assert resp.status_code == 403


def test_unauthenticated_request_is_unauthorized(anon_session, artifacts_url):
    """No Authorization header → 401."""
    resp = anon_session.put(
        f'{artifacts_url}/upload/{STAGING_BUILD}/.final_status',
        data=b'SUCCESSFUL',
        headers={'Script-Name': '/foo'},
    )
    assert resp.status_code == 401
