import os
import sys
import tempfile
import time

# Ensure this directory is on sys.path so test files can import constants.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import boto3
import pytest
import requests
from boto3.exceptions import S3UploadFailedError
from botocore.exceptions import EndpointConnectionError

from constants import BUCKETS


# ---------------------------------------------------------------------------
# Internal helpers (not fixtures)
# ---------------------------------------------------------------------------

def _delete_bucket(client, bucket: str) -> None:
    """Delete a bucket and all its objects."""
    while True:
        objects = client.list_objects(Bucket=bucket)
        content = objects.get('Contents', [])
        if not content:
            break
        for obj in content:
            client.delete_object(Bucket=bucket, Key=obj['Key'])
    client.delete_bucket(Bucket=bucket)


def _s3_healthcheck(client) -> None:
    """Retry S3 connectivity until backend is ready."""
    bucket = 'artifacts-healthcheck'
    filename = tempfile.mktemp()
    with open(filename, 'wb') as fd:
        fd.write(os.urandom(1024))
    try:
        for attempt in range(10):
            try:
                client.create_bucket(Bucket=bucket)
                client.upload_file(filename, bucket, filename)
                _delete_bucket(client, bucket)
                return
            except (S3UploadFailedError, EndpointConnectionError):
                time.sleep(attempt + 1)
        raise RuntimeError("S3 backend never became healthy")
    finally:
        os.remove(filename)


# ---------------------------------------------------------------------------
# Session-scoped fixtures (created once per pytest run)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def s3_client():
    """Boto3 S3 client pointed at the test cloudserver backend."""
    session = boto3.session.Session()
    client = session.client(
        service_name='s3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'accessKey1'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'verySecretKey1'),
        endpoint_url=os.getenv('ENDPOINT_URL', 'http://cloudserver-front:8000'),
    )
    _s3_healthcheck(client)
    return client


@pytest.fixture(scope="session")
def artifacts_url() -> str:
    return os.getenv('ARTIFACTS_URL', 'http://artifacts')


# ---------------------------------------------------------------------------
# Function-scoped fixtures (created fresh for each test)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def managed_buckets(s3_client):
    """Create the three artifact buckets before each test; destroy them after."""
    for bucket in BUCKETS:
        s3_client.create_bucket(Bucket=bucket)
    yield
    for bucket in BUCKETS:
        _delete_bucket(s3_client, bucket)


@pytest.fixture
def session():
    """Requests session authenticated as a user with full upload rights."""
    s = requests.Session()
    s.auth = ('username-pass', 'fake-password')
    return s


@pytest.fixture
def restricted_session():
    """Requests session authenticated as a read-only user (no upload/copy)."""
    s = requests.Session()
    s.auth = ('username-pass-no-restricted-paths', 'fake-password')
    return s


@pytest.fixture
def bot_session():
    """Requests session using the local bot credentials."""
    s = requests.Session()
    s.auth = ('botuser', 'botpass')
    return s


@pytest.fixture
def anon_session():
    """Unauthenticated requests session."""
    return requests.Session()


# ---------------------------------------------------------------------------
# Factory fixtures for common setup operations
# ---------------------------------------------------------------------------

@pytest.fixture
def upload_file(session, artifacts_url):
    """Factory: upload bytes to ``/upload/<build>/<path>``."""
    def _upload(build: str, path: str, data: bytes = b'test content') -> requests.Response:
        url = f'{artifacts_url}/upload/{build}/{path}'
        resp = session.put(url, data=data)
        assert resp.status_code == 200, f'upload {path}: {resp.status_code} {resp.text}'
        return resp
    return _upload


@pytest.fixture
def finish_build(session, artifacts_url):
    """Factory: mark a build finished by uploading ``.final_status``.

    Also sends a ``ForceCacheUpdate`` GET to flush the nginx proxy cache for
    that object, so subsequent ``/copy/`` or ``/last_success/`` calls see it.
    """
    def _finish(build: str, status: str = 'SUCCESSFUL') -> None:
        url = f'{artifacts_url}/upload/{build}/.final_status'
        resp = session.put(url, data=status.encode())
        assert resp.status_code == 200
        # Flush proxy cache
        session.get(
            f'{artifacts_url}/download/{build}/.final_status',
            headers={'ForceCacheUpdate': 'yes'},
        )
    return _finish
