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

    def test_upload_archive(self):
        response_content = cf.upload_archive('aTestContainer',
                                             streamed_archive(b'toto',
                                                              'test_file'))

        self.assertIn(b"201", response_content)

        filecontent = cf.getfile('aTestContainer', 'test_file')

        self.assertEqual(filecontent, b'toto')
