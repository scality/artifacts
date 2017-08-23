import unittest

from artifacts.main import app
from tests.util.stream.archive_stream import streamed_archive


app.testing = True


class ArtifactFlaskTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()

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
