

import boto3
import os
import pytest

@pytest.fixture(scope="class")
def s3_client(request):
    session = boto3.session.Session()
    s3_client = session.client(
        service_name='s3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'accessKey1'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'verySecretKey1'),
        endpoint_url=os.getenv('ENDPOINT_URL', 'http://cloudserver-front:8000')
    )
    request.cls.s3_client = s3_client

@pytest.fixture(scope="class")
def artifacts_url(request):
    request.cls.artifacts_url = os.getenv('ARTIFACTS_URL', 'http://localhost')

@pytest.fixture(scope="class")
def container(request):
    request.cls.container = 'githost:owner:repo:staging-8e50acc6a1.pre-merge.28.1'

@pytest.fixture(scope="class")
def buckets(request):
    buckets = (
        'artifacts-staging',
        'artifacts-promoted',
        'artifacts-prolonged'
    )
    request.cls.buckets = buckets
