"""Tests for the build copy (/copy/) endpoint."""

import pytest

from constants import STAGING_BUILD


COPY_BUILD = f'copy_of_{STAGING_BUILD}'


def test_copy_aborted_when_no_final_status(session, artifacts_url, upload_file):
    """Copy is refused when the source has no .final_status file."""
    for i in range(5):
        upload_file(STAGING_BUILD, f'obj-{i}', b'content')

    resp = session.get(f'{artifacts_url}/copy/{STAGING_BUILD}/{COPY_BUILD}/')
    assert resp.status_code == 200
    last_line = resp.content.splitlines()[-1]
    assert last_line == b'SOURCE BUILD NOT FINISHED (NO ".final_status" FOUND), ABORTING'


def test_copy_succeeds_after_final_status(
    session, artifacts_url, upload_file, finish_build
):
    """Copy succeeds once .final_status is present."""
    for i in range(5):
        upload_file(STAGING_BUILD, f'obj-{i}', b'content')
    finish_build(STAGING_BUILD)

    resp = session.get(f'{artifacts_url}/copy/{STAGING_BUILD}/{COPY_BUILD}/')
    assert resp.status_code == 200
    assert resp.content.splitlines()[-1] == b'BUILD COPIED'


def test_copy_source_and_target_listings_are_identical(
    session, artifacts_url, upload_file, finish_build
):
    """After copy, source and target flat listings are byte-for-byte equal."""
    for i in range(1024):
        upload_file(STAGING_BUILD, f'obj-{i}', b'x')
    finish_build(STAGING_BUILD)

    session.get(f'{artifacts_url}/copy/{STAGING_BUILD}/{COPY_BUILD}/')

    src = session.get(f'{artifacts_url}/download/{STAGING_BUILD}/?format=txt')
    tgt = session.get(f'{artifacts_url}/download/{COPY_BUILD}/?format=txt')
    assert src.status_code == 200
    assert tgt.status_code == 200
    assert len(src.content.splitlines()) == 1026  # 1024 objs + .final_status + .original_build
    assert src.content == tgt.content


def test_copy_fails_when_target_already_exists(
    session, artifacts_url, upload_file, finish_build
):
    """A second copy to the same target is rejected with FAILED."""
    upload_file(STAGING_BUILD, 'file.txt', b'data')
    finish_build(STAGING_BUILD)

    session.get(f'{artifacts_url}/copy/{STAGING_BUILD}/{COPY_BUILD}/')

    # Second attempt — target is not empty
    resp = session.get(f'{artifacts_url}/copy/{STAGING_BUILD}/{COPY_BUILD}/')
    assert resp.status_code == 200
    lines = resp.content.splitlines()
    expected_check_line = (
        b"Checking if the target reference '%b' is empty"
        % COPY_BUILD.encode()
    )
    assert lines[-2] == expected_check_line
    assert lines[-1] == b'FAILED'


def test_copy_behind_ingress(session, artifacts_url, upload_file, finish_build):
    """Copy works correctly when a Script-Name ingress header is present."""
    upload_file(STAGING_BUILD, '.final_status', b'SUCCESSFUL',)
    # flush cache manually (finish_build would also work, but let's stay direct)
    finish_build(STAGING_BUILD)

    resp = session.get(
        f'{artifacts_url}/copy/{STAGING_BUILD}/{COPY_BUILD}/',
        headers={'Script-Name': '/foo'},
    )
    assert resp.status_code == 200
    assert resp.content.splitlines()[-1] == b'BUILD COPIED'

    # Download via ingress path should work too
    dl = session.get(
        f'{artifacts_url}/download/{STAGING_BUILD}/.final_status',
        headers={'Script-Name': '/foo', 'ForceCacheUpdate': 'yes'},
    )
    assert dl.status_code == 200
