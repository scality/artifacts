"""Tests for trailing-slash and Script-Name redirect behaviour."""

import pytest

from constants import STAGING_BUILD


def test_root_redirects_to_builds_with_script_name(session, artifacts_url):
    resp = session.head(
        f'{artifacts_url}/',
        headers={'Script-Name': '/foo'},
    )
    assert resp.status_code == 301
    assert resp.headers['Location'] == f'{artifacts_url}/foo/builds/'


def test_download_without_trailing_slash_redirects(session, artifacts_url):
    resp = session.head(
        f'{artifacts_url}/download/{STAGING_BUILD}',
        headers={'Script-Name': '/foo'},
    )
    assert resp.status_code == 301
    assert resp.headers['Location'] == (
        f'{artifacts_url}/foo/download/{STAGING_BUILD}/'
    )


def test_builds_without_trailing_slash_redirects(session, artifacts_url):
    resp = session.head(
        f'{artifacts_url}/builds/{STAGING_BUILD}',
        headers={'Script-Name': '/foo'},
    )
    assert resp.status_code == 301
    assert resp.headers['Location'] == (
        f'{artifacts_url}/foo/builds/{STAGING_BUILD}/'
    )


def test_download_with_trailing_slash_no_redirect(session, artifacts_url):
    resp = session.head(
        f'{artifacts_url}/download/{STAGING_BUILD}/',
        headers={'Script-Name': '/foo'},
    )
    assert 'Location' not in resp.headers


def test_builds_with_trailing_slash_no_redirect(session, artifacts_url):
    resp = session.head(
        f'{artifacts_url}/builds/{STAGING_BUILD}/',
        headers={'Script-Name': '/foo'},
    )
    assert 'Location' not in resp.headers


def test_download_with_file_path_no_redirect(session, artifacts_url):
    resp = session.head(
        f'{artifacts_url}/download/{STAGING_BUILD}/bar',
        headers={'Script-Name': '/foo'},
    )
    assert 'Location' not in resp.headers


def test_builds_with_file_path_no_redirect(session, artifacts_url):
    resp = session.head(
        f'{artifacts_url}/builds/{STAGING_BUILD}/bar',
        headers={'Script-Name': '/foo'},
    )
    assert 'Location' not in resp.headers
