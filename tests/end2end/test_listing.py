"""Tests for build and root listing endpoints."""

import pytest

from constants import STAGING_BUILD, PROMOTED_BUILD, PROLONGED_BUILD


# ---------------------------------------------------------------------------
# Listing inside a build
# ---------------------------------------------------------------------------

def test_listing_build_directory_returns_200(session, artifacts_url, upload_file):
    upload_file(STAGING_BUILD, '.final_status', b'SUCCESSFUL')

    resp = session.get(f'{artifacts_url}/download/{STAGING_BUILD}/')
    assert resp.status_code == 200


def test_listing_nonexistent_build_html_returns_404(session, artifacts_url):
    resp = session.get(f'{artifacts_url}/download/{STAGING_BUILD}_no_such/')
    assert resp.status_code == 404


def test_listing_nonexistent_build_format_txt_returns_empty(session, artifacts_url):
    """?format=txt on a non-existent prefix returns 200 with empty body."""
    resp = session.get(f'{artifacts_url}/download/{STAGING_BUILD}_no_such/?format=txt')
    assert resp.status_code == 200
    assert resp.content == b''


def test_listing_nonexistent_build_format_text_returns_empty(session, artifacts_url):
    resp = session.get(f'{artifacts_url}/download/{STAGING_BUILD}_no_such/?format=text')
    assert resp.status_code == 200
    assert resp.content == b''


def test_listing_pagination_over_1000_objects(session, artifacts_url, upload_file):
    """Artifacts correctly paginates beyond S3's 1000-key page limit."""
    upload_file(STAGING_BUILD, '.final_status', b'SUCCESSFUL')
    for i in range(1024):
        upload_file(STAGING_BUILD, f'obj-{i}', b'x')

    resp_text = session.get(f'{artifacts_url}/download/{STAGING_BUILD}/?format=text')
    assert resp_text.status_code == 200
    assert len(resp_text.content.splitlines()) == 1025  # 1024 + .final_status

    resp_txt = session.get(f'{artifacts_url}/download/{STAGING_BUILD}/?format=txt')
    assert resp_txt.status_code == 200
    assert len(resp_txt.content.splitlines()) == 1025


def test_listing_format_txt_matches_format_text_when_no_subdirs(
    session, artifacts_url, upload_file
):
    """With no subdirectories, ?format=txt and ?format=text output are identical."""
    upload_file(STAGING_BUILD, '.final_status', b'SUCCESSFUL')
    for i in range(1024):
        upload_file(STAGING_BUILD, f'obj-{i}', b'x')

    resp_text = session.get(f'{artifacts_url}/download/{STAGING_BUILD}/?format=text')
    resp_txt  = session.get(f'{artifacts_url}/download/{STAGING_BUILD}/?format=txt')
    assert resp_text.status_code == 200
    assert resp_txt.status_code == 200
    assert resp_text.content == resp_txt.content


# ---------------------------------------------------------------------------
# Root listing (aggregates all three buckets)
# ---------------------------------------------------------------------------

def test_root_listing_includes_staging_builds(session, artifacts_url, upload_file):
    """The root /download/ listing exposes builds from the staging bucket."""
    upload_file(STAGING_BUILD, 'file.txt', b'data')

    resp = session.get(f'{artifacts_url}/download/?format=text')
    assert resp.status_code == 200
    assert STAGING_BUILD + '/' in resp.text


def test_root_listing_includes_promoted_and_prolonged_builds(
    session, artifacts_url, s3_client
):
    """Root listing aggregates staging, promoted, and prolonged buckets."""
    # Insert objects directly into promoted and prolonged buckets
    s3_client.put_object(
        Bucket='artifacts-promoted',
        Key=f'{PROMOTED_BUILD}/file.txt',
        Body=b'promoted',
    )
    s3_client.put_object(
        Bucket='artifacts-prolonged',
        Key=f'{PROLONGED_BUILD}/file.txt',
        Body=b'prolonged',
    )

    # Use ?format=text to bypass the HTML full-listing cache and query S3 live.
    resp = session.get(f'{artifacts_url}/download/?format=text')
    assert resp.status_code == 200
    assert PROMOTED_BUILD + '/'  in resp.text
    assert PROLONGED_BUILD + '/' in resp.text
