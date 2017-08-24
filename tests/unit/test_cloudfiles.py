import unittest

from tests.util.stream.archive_stream import streamed_archive
from artifacts.providers.cloudfiles import CloudFiles


api_endpoint = 'https://storage101.dfw1.clouddrive.com/v1'
tenant_id = 'MossoCloudFS_984990'
auth_url = 'https://identity.api.rackspacecloud.com/v2.0/tokens'

cf = CloudFiles(api_endpoint, tenant_id, auth_url)


class CloudFilesTestCase(unittest.TestCase):

    def tearDown(self):
        cf.delete_object('aTestContainer', 'test_file')
        cf.delete_container('aTestContainer')

    def test_authenticate(self):
        token = cf.authenticate()

        self.assertEqual(len(token), 142)

    def test_upload_archive_and_getfile(self):
        response = cf.upload_archive('aTestContainer',
                                     streamed_archive('test_file', b'toto'))
        self.assertEqual(200, response.status_code)

        response = cf.getfile('aTestContainer', 'test_file')
        self.assertEqual(response.content, b'toto')
