import unittest

from artifacts.main import app
from tests.util.stream.archive_stream import streamed_archive


app.testing = True


class ArtifactFlaskTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()

        self.outputStream = streamed_archive(b'toto', 'test_file')

    def tearDown(self):
        pass

    def test_POST(self):

        response = self.app.put('/upload/aTestContainer',
                                data=self.outputStream)

        self.assertEqual(response.status_code, 200)

        response = self.app.get('/getfile/aTestContainer/test_file')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b'toto')
