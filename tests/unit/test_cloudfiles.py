import unittest

from tests.util.stream.archive_stream import streamed_archive
from artifacts.providers import CloudFiles
from artifacts.main import api_endpoint, tenant_id, auth_url


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
                                     streamed_archive(b'toto', 'test_file'))
        self.assertEqual(200, response.status_code)

        response = cf.getfile('aTestContainer', 'test_file')
        self.assertEqual(response.content, b'toto')
