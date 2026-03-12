"""Tests for the /add_metadata/ and /search/ endpoints."""

import pytest

from constants import STAGING_BUILD

# Build names used in these tests (must be staging so they are uploadable)
BUILD1 = STAGING_BUILD + '1'
BUILD2 = STAGING_BUILD + '2'
BUILD3 = STAGING_BUILD + '3'

REPO   = 'github/scality/my_repo/my_workflow'
DATE1  = 'my_created_at_1'
DATE2  = 'my_created_at_2'
DATE0  = 'my_created_at_0'


def _upload_sentinel(session, artifacts_url, build):
    resp = session.put(f'{artifacts_url}/upload/{build}/.something', data=b'')
    assert resp.status_code == 200


def _add_metadata(session, artifacts_url, date, build, params='key1=11&key2=22'):
    url = f'{artifacts_url}/add_metadata/{REPO}/{date}/{build}?{params}'
    resp = session.get(url)
    assert resp.status_code == 200


def _search_list(session, artifacts_url, key, value):
    url = f'{artifacts_url}/search/list/{key}/{REPO}/{value}'
    resp = session.get(url)
    assert resp.status_code == 200
    return resp.content.decode()


def _search_last_success(session, artifacts_url, key, value):
    url = f'{artifacts_url}/search/last_success/{key}/{REPO}/{value}'
    resp = session.get(url)
    assert resp.status_code == 200
    return resp.content.decode()


def _search_latest(session, artifacts_url, key, value):
    url = f'{artifacts_url}/search/latest/{key}/{REPO}/{value}'
    resp = session.get(url)
    assert resp.status_code == 200
    return resp.content.decode()


def test_metadata_list_returns_empty_before_indexing(session, artifacts_url):
    _upload_sentinel(session, artifacts_url, BUILD2)
    result = _search_list(session, artifacts_url, 'key2', '22')
    assert result == ''


def test_metadata_list_returns_indexed_build(session, artifacts_url):
    _upload_sentinel(session, artifacts_url, BUILD2)
    _add_metadata(session, artifacts_url, DATE1, BUILD2)

    result = _search_list(session, artifacts_url, 'key2', '22')
    assert result == f'{BUILD2}\n'


def test_metadata_list_with_wrong_key_returns_empty(session, artifacts_url):
    _upload_sentinel(session, artifacts_url, BUILD2)
    _add_metadata(session, artifacts_url, DATE1, BUILD2)

    result = _search_list(session, artifacts_url, 'key2', '11')  # wrong value
    assert result == ''


def test_metadata_list_sorted_by_created_at(session, artifacts_url):
    """Multiple indexed builds appear sorted by their created_at timestamp."""
    for build in (BUILD1, BUILD2, BUILD3):
        _upload_sentinel(session, artifacts_url, build)

    _add_metadata(session, artifacts_url, DATE1, BUILD2)
    _add_metadata(session, artifacts_url, DATE2, BUILD1)
    _add_metadata(session, artifacts_url, DATE0, BUILD3)

    result = _search_list(session, artifacts_url, 'key2', '22')
    assert result == f'{BUILD1}\n{BUILD2}\n{BUILD3}\n'


def test_search_last_success_returns_empty_without_final_status(session, artifacts_url):
    _upload_sentinel(session, artifacts_url, BUILD2)
    _add_metadata(session, artifacts_url, DATE1, BUILD2)

    result = _search_last_success(session, artifacts_url, 'key2', '22')
    assert result == ''


def test_search_latest_returns_empty_without_final_status(session, artifacts_url):
    _upload_sentinel(session, artifacts_url, BUILD2)
    _add_metadata(session, artifacts_url, DATE1, BUILD2)

    result = _search_latest(session, artifacts_url, 'key2', '22')
    assert result == ''


def test_search_last_success_returns_build_after_marking_successful(
    session, artifacts_url
):
    for build in (BUILD1, BUILD2, BUILD3):
        _upload_sentinel(session, artifacts_url, build)

    _add_metadata(session, artifacts_url, DATE1, BUILD2)
    _add_metadata(session, artifacts_url, DATE2, BUILD1)
    _add_metadata(session, artifacts_url, DATE0, BUILD3)

    # Mark build2 and build3 as SUCCESSFUL
    for build in (BUILD2, BUILD3):
        session.put(
            f'{artifacts_url}/upload/{build}/.final_status', data=b'SUCCESSFUL'
        )

    # last_success should be build2 (earliest created_at among successful)
    result = _search_last_success(session, artifacts_url, 'key2', '22')
    assert result == f'{BUILD2}\n'

    # latest (regardless of status) should also be build2
    result = _search_latest(session, artifacts_url, 'key2', '22')
    assert result == f'{BUILD2}\n'


def test_search_last_success_redirect_mode(session, artifacts_url):
    _upload_sentinel(session, artifacts_url, BUILD2)
    _add_metadata(session, artifacts_url, DATE1, BUILD2)
    session.put(
        f'{artifacts_url}/upload/{BUILD2}/.final_status', data=b'SUCCESSFUL'
    )

    url = (
        f'{artifacts_url}/search/last_success/key2/{REPO}/22?output=redirect'
    )
    resp = session.get(url, allow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers['Location'] == f'/download/{BUILD2}/'


def test_search_latest_redirect_mode(session, artifacts_url):
    _upload_sentinel(session, artifacts_url, BUILD2)
    _add_metadata(session, artifacts_url, DATE1, BUILD2)
    session.put(
        f'{artifacts_url}/upload/{BUILD2}/.final_status', data=b'FAILED'
    )

    url = (
        f'{artifacts_url}/search/latest/key2/{REPO}/22?output=redirect'
    )
    resp = session.get(url, allow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers['Location'] == f'/download/{BUILD2}/'


def test_search_last_success_redirect_mode_no_match_is_404(session, artifacts_url):
    url = (
        f'{artifacts_url}/search/last_success/key2/{REPO}/22?output=redirect'
    )
    resp = session.get(url, allow_redirects=False)
    assert resp.status_code == 404


def test_search_last_success_skips_failed_builds(session, artifacts_url):
    for build in (BUILD1, BUILD2, BUILD3):
        _upload_sentinel(session, artifacts_url, build)
    _add_metadata(session, artifacts_url, DATE2, BUILD1)
    _add_metadata(session, artifacts_url, DATE1, BUILD2)
    _add_metadata(session, artifacts_url, DATE0, BUILD3)

    # build2 succeeds then fails; build3 succeeds
    session.put(
        f'{artifacts_url}/upload/{BUILD2}/.final_status', data=b'SUCCESSFUL'
    )
    session.put(
        f'{artifacts_url}/upload/{BUILD3}/.final_status', data=b'SUCCESSFUL'
    )
    # Overwrite build2 to FAILED
    session.put(
        f'{artifacts_url}/upload/{BUILD2}/.final_status', data=b'FAILED'
    )

    result = _search_last_success(session, artifacts_url, 'key2', '22')
    assert result == f'{BUILD3}\n'
