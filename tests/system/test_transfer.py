import unittest

from artifacts import main
from artifacts.providers.s3 import S3
from tests.util.stream.archive_stream import streamed_archive

main.app.testing = True
main.provider = S3()


class ArtifactFlaskTestCase(unittest.TestCase):

    def setUp(self):
        self.app = main.app.test_client()

        self.outputStream = streamed_archive('test_file', b'toto')

    def tearDown(self):
        pass

    def test_POST_and_GET(self):

        # Upload test archive
        response = self.app.put('/upload/aTestContainer',
                                data=self.outputStream)

        self.assertEqual(response.status_code, 200)

        # Get test file content
        response = self.app.get('/getfile/aTestContainer/test_file')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b'toto')
