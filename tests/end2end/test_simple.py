
import unittest
import pytest
import requests
import tempfile
import hashlib
import os


@pytest.mark.usefixtures("s3_client", "container", "artifacts_url", "buckets")
class TestSimple(unittest.TestCase):

    def delete_bucket(self, bucket):
        """Utility function to delete a non empty bucket."""
        objects = self.s3_client.list_objects(Bucket=bucket)
        content = objects.get('Contents', [])
        for obj in content:
            self.s3_client.delete_object(Bucket=bucket, Key=obj['Key'])
        self.s3_client.delete_bucket(Bucket=bucket)

    def setUp(self):
        for bucket in self.buckets:
            self.s3_client.create_bucket(Bucket=bucket)

    def tearDown(self):
        for bucket in self.buckets:
            self.delete_bucket(bucket)

    def test_simple_upload_download(self):

        # Uploading a generated file
        filename = tempfile.mktemp()
        url = '{artifacts_url}/upload/{container}{filename}'.format(
            artifacts_url=self.artifacts_url,
            container=self.container,
            filename=filename
        )
        with open(filename, 'wb+') as fd:
            fd.write(os.urandom(1024))
            sha_upload = hashlib.sha256(fd.read()).hexdigest()

            files = {'upload_file': open(filename, 'rb')}
            upload = requests.put(url, files=files)
            assert upload.status_code == 200

        # Downloading the generated file and ensure it is the same
        download_file = tempfile.mktemp()
        url = '{artifacts_url}/download/{container}{filename}'.format(
            artifacts_url=self.artifacts_url,
            container=self.container,
            filename=filename
        )
        with open(download_file, 'wb+') as fd:
            download = requests.get(url)
            assert download.status_code == 200
            fd.write(download.content)
            sha_download = hashlib.sha256(fd.read()).hexdigest()

        assert sha_download == sha_upload

    def test_simple_last_success_get_head(self):
        # Uploading a generated file
        filename = tempfile.mktemp()
        url = '{artifacts_url}/upload/{container}/.final_status'.format(
            artifacts_url=self.artifacts_url,
            container=self.container,
            filename=filename
        )
        success = 'SUCCESSFUL'.encode('utf-8')
        upload = requests.put(url, data=success)
        assert upload.status_code == 200
        head = requests.head('{artifacts_url}/last_success/{container}'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ))
        assert head.headers['Location'] == '/download/{container}/'.format(
            container=self.container)
        assert head.status_code == 302
        get = requests.get('{artifacts_url}/last_success/{container}'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ))
        assert get.status_code == 200
