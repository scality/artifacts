
import unittest
import pytest
import requests
import tempfile
import hashlib
import os
import time

from boto3.exceptions import S3UploadFailedError
from botocore.exceptions import EndpointConnectionError


@pytest.mark.usefixtures("s3_client", "container", "artifacts_url", "buckets")
class TestSimple(unittest.TestCase):
    def delete_bucket(self, bucket):
        """Utility function to delete a non empty bucket."""
        while True:
            objects = self.s3_client.list_objects(Bucket=bucket)
            content = objects.get('Contents', [])
            if len(content) == 0:
                break
            for obj in content:
                self.s3_client.delete_object(Bucket=bucket, Key=obj['Key'])
        self.s3_client.delete_bucket(Bucket=bucket)

    def s3_healthcheck(self):
        """Ensure S3 backend is alive.

        The goal of this function is to ensure that the S3 backend is functionning
        well before starting any kind of tests to avoid race conditions.
        """
        # ensure S3 backend is alive
        retries = 10
        bucket = 'artifacts-healthcheck'
        filename = tempfile.mktemp()
        with open(filename, 'wb+') as fd:
            fd.write(os.urandom(1024))
        for attempt in range(retries):
            try:
                self.s3_client.create_bucket(Bucket=bucket)
                self.s3_client.upload_file(filename, bucket, filename)
                self.delete_bucket(bucket)
                break
            except (
                S3UploadFailedError,
                EndpointConnectionError
            ) as e:
                time.sleep(attempt)
                if attempt == retries:
                    raise
                pass
        os.remove(filename)

    def setUp(self):
        self.session = requests.Session()
        self.session.auth = ('username-pass', 'fake-password')
        self.s3_healthcheck()
        for bucket in self.buckets:
            self.s3_client.create_bucket(Bucket=bucket)

    def tearDown(self):
        for bucket in self.buckets:
            self.delete_bucket(bucket)

    def test_metadata(self):
        # generate 3 builds
        success = 'SUCCESSFUL'.encode('utf-8')
        failure='FAILED'.encode('utf-8')

        url = '{artifacts_url}/upload/{container}1/.something'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        upload = self.session.put(url, data="")
        assert upload.status_code == 200

        url = '{artifacts_url}/upload/{container}2/.something'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        upload = self.session.put(url, data="")
        assert upload.status_code == 200

        url = '{artifacts_url}/upload/{container}3/.something'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        upload = self.session.put(url, data="")
        assert upload.status_code == 200

        # send metadata for container2
        url = '{artifacts_url}/add_metadata/github/scality/my_repo/my_workflow/my_created_at_1/{container}2?key1=11&key2=22'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        request = self.session.get(url)
        assert request.status_code == 200

        # query list with bad key value
        url = '{artifacts_url}/search/list/key2/github/scality/my_repo/my_workflow/11'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        request = self.session.get(url)
        assert request.status_code == 200
        assert request.content.decode("utf-8") == ''

        # query list with good key value
        url = '{artifacts_url}/search/list/key2/github/scality/my_repo/my_workflow/22'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        request = self.session.get(url)
        assert request.status_code == 200
        assert request.content.decode("utf-8") == '{container}2\n'.format(container=self.container)

        # send metadata for container1 and container3
        url = '{artifacts_url}/add_metadata/github/scality/my_repo/my_workflow/my_created_at_2/{container}1?key1=11&key2=22'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        request = self.session.get(url)
        assert request.status_code == 200
        url = '{artifacts_url}/add_metadata/github/scality/my_repo/my_workflow/my_created_at_0/{container}3?key1=11&key2=22'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        request = self.session.get(url)
        assert request.status_code == 200

        # query list
        url = '{artifacts_url}/search/list/key2/github/scality/my_repo/my_workflow/22'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        request = self.session.get(url)
        assert request.status_code == 200
        assert request.content.decode("utf-8") == '{container}1\n{container}2\n{container}3\n'.format(container=self.container)

        # query last_success
        url = '{artifacts_url}/search/last_success/key2/github/scality/my_repo/my_workflow/22'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        request = self.session.get(url)
        assert request.status_code == 200
        assert request.content.decode("utf-8") == ''

        # query latest
        url = '{artifacts_url}/search/latest/key2/github/scality/my_repo/my_workflow/22'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        request = self.session.get(url)
        assert request.status_code == 200
        assert request.content.decode("utf-8") == ''

        # update .final_status for container2 to success
        url = '{artifacts_url}/upload/{container}2/.final_status'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        upload = self.session.put(url, data=success)
        assert upload.status_code == 200

        # update .final_status for container3 to success
        url = '{artifacts_url}/upload/{container}3/.final_status'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        upload = self.session.put(url, data=success)
        assert upload.status_code == 200

        # query list
        url = '{artifacts_url}/search/list/key2/github/scality/my_repo/my_workflow/22'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        request = self.session.get(url)
        assert request.status_code == 200
        assert request.content.decode("utf-8") == '{container}1\n{container}2\n{container}3\n'.format(container=self.container)

        # query last_success
        url = '{artifacts_url}/search/last_success/key2/github/scality/my_repo/my_workflow/22'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        request = self.session.get(url)
        assert request.status_code == 200
        assert request.content.decode("utf-8") == '{container}2\n'.format(container=self.container)

        # query latest
        url = '{artifacts_url}/search/latest/key2/github/scality/my_repo/my_workflow/22'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        request = self.session.get(url)
        assert request.status_code == 200
        assert request.content.decode("utf-8") == '{container}2\n'.format(container=self.container)

        # update .final_status for container2 to failure
        url = '{artifacts_url}/upload/{container}2/.final_status'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        upload = self.session.put(url, data=failure)
        assert upload.status_code == 200

        # query last_success
        url = '{artifacts_url}/search/last_success/key2/github/scality/my_repo/my_workflow/22'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        request = self.session.get(url)
        assert request.status_code == 200
        assert request.content.decode("utf-8") == '{container}3\n'.format(container=self.container)

        # query latest
        url = '{artifacts_url}/search/latest/key2/github/scality/my_repo/my_workflow/22'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        request = self.session.get(url)
        assert request.status_code == 200
        assert request.content.decode("utf-8") == '{container}2\n'.format(container=self.container)

        # update .final_status for container3 to failure
        url = '{artifacts_url}/upload/{container}3/.final_status'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        upload = self.session.put(url, data=failure)
        assert upload.status_code == 200

        # query last_success
        url = '{artifacts_url}/search/last_success/key2/github/scality/my_repo/my_workflow/22'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        request = self.session.get(url)
        assert request.status_code == 200
        assert request.content.decode("utf-8") == ''

        # query latest
        url = '{artifacts_url}/search/latest/key2/github/scality/my_repo/my_workflow/22'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        request = self.session.get(url)
        assert request.status_code == 200
        assert request.content.decode("utf-8") == '{container}2\n'.format(container=self.container)


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
            upload = self.session.put(url, files=files)
            assert upload.status_code == 200

        # Downloading the generated file and ensure it is the same
        download_file = tempfile.mktemp()
        url = '{artifacts_url}/download/{container}{filename}'.format(
            artifacts_url=self.artifacts_url,
            container=self.container,
            filename=filename
        )
        with open(download_file, 'wb+') as fd:
            download = self.session.get(url, headers={'ForceCacheUpdate': 'yes'})
            assert download.status_code == 200
            fd.write(download.content)
            sha_download = hashlib.sha256(fd.read()).hexdigest()

        assert sha_download == sha_upload

        # Downloading via redirect the generated file and ensure it is the same
        download_file = tempfile.mktemp()
        url = '{artifacts_url}/redirect/{container}{filename}'.format(
            artifacts_url=self.artifacts_url,
            container=self.container,
            filename=filename
        )
        with open(download_file, 'wb+') as fd:
            download = self.session.get(url)
            assert download.status_code == 200
            fd.write(download.content)
            sha_download = hashlib.sha256(fd.read()).hexdigest()

        assert sha_download == sha_upload

        # Download through full url with repo ref inside
        download_file = tempfile.mktemp()
        url = '{artifacts_url}/github/scality/fakerepo/builds/{container}{filename}'.format(
            artifacts_url=self.artifacts_url,
            container=self.container,
            filename=filename
        )
        with open(download_file, 'wb+') as fd:
            download = self.session.get(url, headers={'ForceCacheUpdate': 'yes'})
            assert download.status_code == 200
            fd.write(download.content)
            sha_download = hashlib.sha256(fd.read()).hexdigest()

        assert sha_download == sha_upload

    def test_simple_upload_and_version(self):

        # Mimic an upload behind the ingress
        url = '{artifacts_url}/upload/{container}/.final_status'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        success = 'SUCCESSFUL'.encode('utf-8')
        upload = self.session.put(url, data=success)
        assert upload.status_code == 200

        # Mimic a version
        url = '{artifacts_url}/version/42/{container}/.final_status'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        copy = self.session.get(url)
        assert copy.status_code == 200

        # Download the versioned object
        get = self.session.get('{artifacts_url}/download/{container}/.ARTIFACTS_BEFORE/42/.final_status'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ))
        assert get.status_code == 200

    def test_simple_upload_and_copy_behind_ingress(self):

        # Mimic an upload behind the ingress
        url = '{artifacts_url}/upload/{container}/.final_status'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        success = 'SUCCESSFUL'.encode('utf-8')
        upload = self.session.put(url, data=success, headers={'Script-Name': '/foo'})
        assert upload.status_code == 200

        # Mimic a copy behind the ingress
        url = '{artifacts_url}/copy/{container}/copy_of_{container}/'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        success = 'SUCCESSFUL'.encode('utf-8')
        copy = self.session.get(url, data=success, headers={'Script-Name': '/foo'})
        assert copy.status_code == 200

        # Upload without ingress and download with ingress
        url = '{artifacts_url}/upload/{container}/.final_status'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        success = 'SUCCESSFUL'.encode('utf-8')
        upload = self.session.put(url, data=success)
        assert upload.status_code == 200
        get = self.session.get('{artifacts_url}/download/{container}/.final_status'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ), headers={'Script-Name': '/foo', 'ForceCacheUpdate': 'yes'})
        assert get.status_code == 200

    def test_simple_listing_inside_a_build(self):
        url = '{artifacts_url}/upload/{container}/.final_status'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        success = 'SUCCESSFUL'.encode('utf-8')
        upload = self.session.put(url, data=success)
        assert upload.status_code == 200
        get = self.session.get('{artifacts_url}/download/{container}/'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ))
        assert get.status_code == 200
        get = self.session.get('{artifacts_url}/download/{container}_do_not_exist/'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ))
        assert get.status_code == 404
        get = self.session.get('{artifacts_url}/download/{container}_do_not_exist/?format=txt'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ))
        assert get.status_code == 200
        assert get.content == b""
        get = self.session.get('{artifacts_url}/download/{container}_do_not_exist/?format=text'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ))
        assert get.status_code == 200
        assert get.content == b""

        # Listing more than 1000 keys
        for i in range(1024):
            url = '{artifacts_url}/upload/{container}/obj-{suffix}'.format(
                artifacts_url=self.artifacts_url,
                container=self.container,
                suffix=i
            )
            success = 'SUCCESSFUL'.encode('utf-8')
            upload = self.session.put(url, data=success)
            assert upload.status_code == 200
        get_text = self.session.get('{artifacts_url}/download/{container}/?format=text'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ))
        assert get_text.status_code == 200
        assert len(get_text.content.splitlines()) == 1025

        # Trigger a zenko cloud server bug (no NextMarker received for a truncated listing when no Delimiter is sent)
        # Check that artifacts can handle it
        get_txt = self.session.get('{artifacts_url}/download/{container}/?format=txt'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ))
        assert get_txt.status_code == 200
        assert len(get_txt.content.splitlines()) == 1025

        # Because there is no "subdir" those two listing must be the same
        assert get_text.content == get_txt.content

    def test_simple_build_copy(self):

        for i in range(1024):
            url = '{artifacts_url}/upload/{container}/obj-{suffix}'.format(
                artifacts_url=self.artifacts_url,
                container=self.container,
                suffix=i
            )
            success = 'SUCCESSFUL'.encode('utf-8')
            upload = self.session.put(url, data=success)
            assert upload.status_code == 200

        get = self.session.get('{artifacts_url}/copy/{container}/copy_of_{container}/'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ))
        assert get.status_code == 200
        assert get.content.splitlines()[-1] == b'SOURCE BUILD NOT FINISHED (NO ".final_status" FOUND), ABORTING'

        url = '{artifacts_url}/upload/{container}/.final_status'.format(
                artifacts_url=self.artifacts_url,
                container=self.container
        )
        success = 'SUCCESSFUL'.encode('utf-8')
        upload = self.session.put(url, data=success)
        assert upload.status_code == 200

        # Refresh artifacts cache for .final_status
        get = self.session.get('{artifacts_url}/download/{container}/.final_status'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ), headers={'ForceCacheUpdate': 'yes'})
        assert get.status_code == 200

        get = self.session.get('{artifacts_url}/copy/{container}/copy_of_{container}/'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ))
        assert get.status_code == 200
        assert get.content.splitlines()[-1] == b'BUILD COPIED'

        # Compare source and target listings
        get_src = self.session.get('{artifacts_url}/download/{container}/?format=txt'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ))
        get_tgt = self.session.get('{artifacts_url}/download/copy_of_{container}/?format=txt'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ))
        assert get_src.status_code == 200
        assert get_tgt.status_code == 200
        assert len(get_src.content.splitlines()) == 1026
        assert len(get_tgt.content.splitlines()) == 1026
        assert get_src.content == get_tgt.content

        # This should fail because copy already exists
        get = self.session.get('{artifacts_url}/copy/{container}/copy_of_{container}/'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ))
        assert get.status_code == 200
        assert get.content.splitlines()[-2] == b'Checking if the target reference \'copy_of_%b\' is empty' % bytes(self.container, encoding='utf-8')
        assert get.content.splitlines()[-1] == b'FAILED'

    def test_simple_last_success_get_head(self):
        # Test a direct upload
        url = '{artifacts_url}/upload/{container}/.final_status'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        success = 'SUCCESSFUL'.encode('utf-8')
        upload = self.session.put(url, data=success)
        assert upload.status_code == 200

        # Refresh artifacts cache for .final_status
        get = self.session.get('{artifacts_url}/download/{container}/.final_status'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ), headers={'ForceCacheUpdate': 'yes'})
        assert get.status_code == 200

        # Check HEAD and GET on the object uploaded
        head = self.session.head('{artifacts_url}/last_success/{container}'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ))
        assert head.headers['Location'] == '/download/{container}/'.format(
            container=self.container)
        assert head.status_code == 302
        get = self.session.get('{artifacts_url}/last_success/{container}'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ))
        assert get.status_code == 200

    def test_simple_redirections(self):
        req = self.session.head('{artifacts_url}/'.format(
            artifacts_url=self.artifacts_url
        ), headers={'Script-Name': '/foo'})
        assert req.headers['Location'] == '{artifacts_url}/foo/builds/'.format(
            artifacts_url=self.artifacts_url)
        assert req.status_code == 301

        req = self.session.head('{artifacts_url}/download/{container}'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ), headers={'Script-Name': '/foo'})
        assert req.headers['Location'] == '{artifacts_url}/foo/download/{container}/'.format(
            artifacts_url=self.artifacts_url,
            container=self.container)
        assert req.status_code == 301

        req = self.session.head('{artifacts_url}/builds/{container}'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ), headers={'Script-Name': '/foo'})
        assert req.headers['Location'] == '{artifacts_url}/foo/builds/{container}/'.format(
            artifacts_url=self.artifacts_url,
            container=self.container)
        assert req.status_code == 301

        req = self.session.head('{artifacts_url}/download/{container}/'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ), headers={'Script-Name': '/foo'})
        assert 'Location' not in req.headers

        req = self.session.head('{artifacts_url}/builds/{container}/'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ), headers={'Script-Name': '/foo'})
        assert 'Location' not in req.headers

        req = self.session.head('{artifacts_url}/download/{container}/bar'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ), headers={'Script-Name': '/foo'})
        assert 'Location' not in req.headers

        req = self.session.head('{artifacts_url}/builds/{container}/bar'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        ), headers={'Script-Name': '/foo'})
        assert 'Location' not in req.headers


@pytest.mark.usefixtures("s3_client", "container", "artifacts_url", "buckets")
class TestExternalBasicAuthentication(unittest.TestCase):
    def delete_bucket(self, bucket):
        """Utility function to delete a non empty bucket."""
        while True:
            objects = self.s3_client.list_objects(Bucket=bucket)
            content = objects.get('Contents', [])
            if len(content) == 0:
                break
            for obj in content:
                self.s3_client.delete_object(Bucket=bucket, Key=obj['Key'])
        self.s3_client.delete_bucket(Bucket=bucket)

    def s3_healthcheck(self):
        """Ensure S3 backend is alive.

        The goal of this function is to ensure that the S3 backend is functionning
        well before starting any kind of tests to avoid race conditions.
        """
        # ensure S3 backend is alive
        retries = 10
        bucket = 'artifacts-healthcheck'
        filename = tempfile.mktemp()
        with open(filename, 'wb+') as fd:
            fd.write(os.urandom(1024))
        for attempt in range(retries):
            try:
                self.s3_client.create_bucket(Bucket=bucket)
                self.s3_client.upload_file(filename, bucket, filename)
                self.delete_bucket(bucket)
                break
            except (
                    S3UploadFailedError,
                    EndpointConnectionError
            ) as e:
                time.sleep(attempt)
                if attempt == retries:
                    raise
                pass
        os.remove(filename)

    def setUp(self):
        self.session = requests.Session()
        self.s3_healthcheck()
        for bucket in self.buckets:
            self.s3_client.create_bucket(Bucket=bucket)

    def tearDown(self):
        for bucket in self.buckets:
            self.delete_bucket(bucket)

    def test_successful_user(self):
        self.session.auth = ('username-pass', 'fake-password')

        # Mimic an upload behind the ingress
        url = '{artifacts_url}/upload/{container}/.final_status'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        success = 'SUCCESSFUL'.encode('utf-8')
        upload = self.session.put(url, data=success, headers={'Script-Name': '/foo'})
        assert upload.status_code == 200

    def test_local_bot_user(self):
        self.session.auth = ('botuser', 'botpass')

        # Mimic a download
        url = '{artifacts_url}/download/{container}'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        listing = self.session.get(url)
        assert listing.status_code == 404

    def test_successful_user_not_allowed_to_restricted_paths (self):
        self.session.auth = ('username-pass-no-restricted-paths', 'fake-password')

        # Mimic a download
        url = '{artifacts_url}/download/{container}/'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        upload = self.session.get(url)
        assert upload.status_code == 404

        # Mimic an upload
        url = '{artifacts_url}/upload/{container}/.final_status'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        success = 'SUCCESSFUL'.encode('utf-8')
        upload = self.session.put(url, data=success)
        assert upload.status_code == 403

        # Mimic a copy
        url = '{artifacts_url}/copy/{container}/copy_of_{container}/'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        copy = self.session.get(url)
        assert copy.status_code == 403

        # Mimic a metadata upload
        url = '{artifacts_url}/add_metadata/fake/args'.format(
            artifacts_url=self.artifacts_url
        )
        copy = self.session.get(url)
        assert copy.status_code == 403

    def test_fail_user(self):
        self.session.auth = ('username-fail', 'fake-password')

        # Mimic an upload behind the ingress
        url = '{artifacts_url}/upload/{container}/.final_status'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        success = 'SUCCESSFUL'.encode('utf-8')
        upload = self.session.put(url, data=success, headers={'Script-Name': '/foo'})
        assert upload.status_code == 403

    def test_no_user(self):
        url = '{artifacts_url}/upload/{container}/.final_status'.format(
            artifacts_url=self.artifacts_url,
            container=self.container
        )
        success = 'SUCCESSFUL'.encode('utf-8')
        upload = self.session.put(url, data=success, headers={'Script-Name': '/foo'})
        assert upload.status_code == 401
