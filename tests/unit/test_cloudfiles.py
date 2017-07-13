import unittest

from tests.util.stream.archive_stream import streamed_archive
from artifacts.providers import CloudFiles


api_endpoint = 'https://storage101.dfw1.clouddrive.com'
tenant_id = 'MossoCloudFS_984990'
cf = CloudFiles(api_endpoint, tenant_id)


class CloudFilesTestCase(unittest.TestCase):

    def test_authenticate(self):
        token = cf.authenticate()

        self.assertEqual(len(token), 142)

    def test_upload_archive(self):
        code = cf.upload_archive(streamed_archive(b'toto', 'test_file'),
                                 'test_container')
        self.assertEqual(code, 200)

        filecontent = cf.getfile('test_file', 'test_container')

        self.assertEqual(filecontent, b'toto')
