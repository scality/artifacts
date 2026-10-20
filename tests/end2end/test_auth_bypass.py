"""Regression tests for authentication / authorization bypasses (PTFE-3620).

1. Locations whose Lua handler ends the request during nginx's rewrite phase
   (ngx.redirect / ngx.say + ngx.exit) used to skip github_access.lua, which
   runs in the later access phase. Anonymous clients could then:
     - download any file through /builds/ with a non-browser User-Agent
       (rewritten to /redirect/) or directly through /redirect/,
     - obtain presigned S3 PUT URLs from /presign-upload/ and
       /presign-upload-part/,
     - enumerate build names through /latest/, /last_success/, /last_failure/.

2. The upload-restricted paths check compared the raw request URI, while nginx
   routes on the decoded one, so a percent-encoded first segment
   (e.g. /%75pload/) let a user outside GITHUB_USER_ALLOWED_UPLOAD write.
"""

import base64
import http.client
from urllib.parse import urlparse

import pytest
import requests

from constants import STAGING_BUILD, PROMOTED_BUILD


# Non-browser User-Agents that are routed to /redirect/ by the /builds/ map.
# None removes the header entirely.
CLI_USER_AGENTS = [
    'curl/8.5.0',
    'Wget/1.21.4',
    'python-requests/2.31.0',
    'Slackbot-LinkExpanding 1.0',
    '',
    None,
]


RESTRICTED_AUTH = ('username-pass-no-restricted-paths', 'fake-password')


def raw_request(artifacts_url, method, path, auth=RESTRICTED_AUTH, body=None):
    """Send ``path`` verbatim: requests would decode %75 back to 'u'."""
    url = urlparse(artifacts_url)
    conn = http.client.HTTPConnection(url.hostname, url.port or 80, timeout=30)
    headers = {}
    if auth:
        token = base64.b64encode(':'.join(auth).encode()).decode()
        headers['Authorization'] = f'Basic {token}'
    conn.request(method, path, body=body, headers=headers)
    resp = conn.getresponse()
    resp.read()
    conn.close()
    return resp.status


@pytest.fixture
def stored_file(s3_client):
    """Put an object straight into the promoted bucket and return its path."""
    path = f'{PROMOTED_BUILD}/secret.txt'
    s3_client.put_object(Bucket='artifacts-promoted', Key=path, Body=b'secret')
    return path


# ---------------------------------------------------------------------------
# Anonymous downloads
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('user_agent', CLI_USER_AGENTS)
def test_anonymous_builds_download_is_unauthorized(
    anon_session, artifacts_url, stored_file, user_agent
):
    resp = anon_session.get(
        f'{artifacts_url}/builds/{stored_file}',
        headers={'User-Agent': user_agent},
        allow_redirects=False,
    )
    assert resp.status_code == 401, resp.headers.get('Location')


@pytest.mark.parametrize('method', ['GET', 'HEAD'])
def test_anonymous_redirect_is_unauthorized(
    anon_session, artifacts_url, stored_file, method
):
    resp = anon_session.request(
        method,
        f'{artifacts_url}/redirect/{stored_file}',
        allow_redirects=False,
    )
    assert resp.status_code == 401, resp.headers.get('Location')


def test_anonymous_github_builds_download_is_unauthorized(
    anon_session, artifacts_url, stored_file
):
    resp = anon_session.get(
        f'{artifacts_url}/github/scality/repo/builds/{stored_file}',
        headers={'User-Agent': 'curl/8.5.0'},
        allow_redirects=False,
    )
    assert resp.status_code == 401


def test_authenticated_cli_download_still_redirects(
    session, artifacts_url, stored_file
):
    resp = session.get(
        f'{artifacts_url}/builds/{stored_file}',
        headers={'User-Agent': 'curl/8.5.0'},
        allow_redirects=False,
    )
    assert resp.status_code == 302
    s3 = requests.get(resp.headers['Location'])
    assert s3.status_code == 200
    assert s3.content == b'secret'


# ---------------------------------------------------------------------------
# Anonymous / restricted presigned uploads
# ---------------------------------------------------------------------------

PRESIGN_URLS = [
    f'/presign-upload/{STAGING_BUILD}/file.txt',
    f'/presign-upload-part/{STAGING_BUILD}/file.txt?partNumber=1&uploadId=abc',
]


@pytest.mark.parametrize('path', PRESIGN_URLS)
def test_anonymous_presign_upload_is_unauthorized(anon_session, artifacts_url, path):
    resp = anon_session.get(f'{artifacts_url}{path}')
    assert resp.status_code == 401, resp.text


@pytest.mark.parametrize('path', PRESIGN_URLS)
def test_restricted_user_cannot_presign_upload(
    restricted_session, artifacts_url, path
):
    resp = restricted_session.get(f'{artifacts_url}{path}')
    assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# Anonymous build discovery
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('endpoint', ['latest', 'last_success', 'last_failure'])
def test_anonymous_find_build_is_unauthorized(
    anon_session, artifacts_url, upload_file, finish_build, endpoint
):
    upload_file(STAGING_BUILD, 'file.txt')
    finish_build(STAGING_BUILD, 'FAILED' if endpoint == 'last_failure' else 'SUCCESSFUL')
    prefix = STAGING_BUILD.rsplit('.', 1)[0]
    resp = anon_session.get(
        f'{artifacts_url}/{endpoint}/{prefix}',
        allow_redirects=False,
    )
    assert resp.status_code == 401, resp.headers.get('Location')


# ---------------------------------------------------------------------------
# Upload restriction bypass through percent-encoded paths
# ---------------------------------------------------------------------------

def test_restricted_user_cannot_upload_with_encoded_path(artifacts_url, s3_client):
    status = raw_request(
        artifacts_url, 'PUT', f'/%75pload/{STAGING_BUILD}/file.txt', body=b'pwned'
    )
    assert status == 403
    objs = s3_client.list_objects(Bucket='artifacts-staging')
    assert objs.get('Contents') is None


def test_restricted_user_cannot_multipart_initiate_with_encoded_path(artifacts_url):
    status = raw_request(
        artifacts_url, 'POST', f'/%75pload-multipart/initiate/{STAGING_BUILD}/file.txt'
    )
    assert status == 403


@pytest.mark.parametrize('path', [
    f'/%70resign-upload/{STAGING_BUILD}/file.txt',
    f'/%70resign-upload-part/{STAGING_BUILD}/file.txt?partNumber=1&uploadId=abc',
])
def test_restricted_user_cannot_presign_upload_with_encoded_path(artifacts_url, path):
    assert raw_request(artifacts_url, 'GET', path) == 403


def test_restricted_user_cannot_copy_with_encoded_path(
    artifacts_url, upload_file, finish_build, s3_client
):
    upload_file(STAGING_BUILD, 'file.txt')
    finish_build(STAGING_BUILD)
    status = raw_request(
        artifacts_url, 'GET', f'/c%6Fpy/{STAGING_BUILD}/{PROMOTED_BUILD}/'
    )
    assert status == 403
    objs = s3_client.list_objects(Bucket='artifacts-promoted')
    assert objs.get('Contents') is None


def test_restricted_user_cannot_add_metadata_with_encoded_path(artifacts_url):
    status = raw_request(
        artifacts_url, 'GET', '/%61dd_metadata/github/scality/repo/wf/1/name?k=v'
    )
    assert status == 403


def test_restricted_user_cannot_version_with_encoded_path(artifacts_url):
    status = raw_request(
        artifacts_url, 'GET', f'/%76ersion/1/{STAGING_BUILD}/file.txt'
    )
    assert status == 403


# ---------------------------------------------------------------------------
# /github/scality/<repo>/(builds|download)/ internal hop
# ---------------------------------------------------------------------------
#
# This location proxies to 127.0.0.1, where github_access.lua skips every
# check. A double-encoded '..' (%252e) used to survive the first decoding and
# be normalized by the inner request, reaching any location from localhost.

def test_restricted_user_cannot_copy_through_github_alias(
    artifacts_url, upload_file, finish_build, s3_client
):
    upload_file(STAGING_BUILD, 'file.txt')
    finish_build(STAGING_BUILD)
    up = '%252e%252e/' * 3
    status = raw_request(
        artifacts_url, 'GET',
        f'/github/scality/repo/builds/{STAGING_BUILD}/{PROMOTED_BUILD}/{up}'
        f'copy/{STAGING_BUILD}/{PROMOTED_BUILD}/',
    )
    # The inner request stays under /download/ and fails the charset check.
    assert status == 400
    objs = s3_client.list_objects(Bucket='artifacts-promoted')
    assert objs.get('Contents') is None


def test_github_alias_rejects_writes(artifacts_url):
    status = raw_request(
        artifacts_url, 'PUT',
        f'/github/scality/repo/builds/{STAGING_BUILD}/file.txt',
        auth=('username-pass', 'fake-password'), body=b'x',
    )
    assert status == 400


def test_github_alias_listing_filters_on_repo(session, artifacts_url, upload_file):
    """The alias must pass the repo name in Script-Name: the root listing is
    filtered on the github:scality:<repo>: prefix built from it."""
    build = 'github:scality:repo:staging-8e50acc6a1.pre-merge.28.1'
    other = 'github:scality:other:staging-8e50acc6a1.pre-merge.28.1'
    upload_file(build, 'file.txt')
    upload_file(other, 'file.txt')
    resp = session.get(f'{artifacts_url}/github/scality/repo/builds/?format=text')
    assert resp.status_code == 200
    assert f'{build}/' in resp.text.splitlines()
    assert f'{other}/' not in resp.text.splitlines()


def test_github_alias_rejects_header_injection_in_repo(
    artifacts_url, stored_file
):
    """The repo name is copied into the Script-Name header of the inner
    request; a decoded CR/LF there must not be proxied."""
    status = raw_request(
        artifacts_url, 'GET',
        f'/github/scality/repo%0d%0aX-Injected:%20yes/download/{stored_file}',
        auth=('username-pass', 'fake-password'),
    )
    assert status == 404
