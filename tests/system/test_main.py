import unittest

from artifacts.main import artifact_flask as af
from tests.util.stream.archive_stream import streamed_archive


af.testing = True


class ArtifactFlaskTestCase(unittest.TestCase):

    def setUp(self):
        self.af = af.test_client()

        self.outputStream = streamed_archive(b'toto')

    def tearDown(self):
        pass

    def test_POST(self):

        response = self.af.put('/upload_archive/mycontainer',
                               data=self.outputStream)
        print(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b'archive saved')

        response = self.af.get('/getfile/mycontainer/README')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b'toto')
