import unittest
import io
import tarfile

from artifacts.main import artifact_flask as af


af.testing = True


class ArtifactFlaskTestCase(unittest.TestCase):

    def setUp(self):
        self.af = af.test_client()

        self.outputStream = io.BytesIO()
        tar = tarfile.open(fileobj=self.outputStream, mode='w:gz')
        inputStream = io.BytesIO(b'toto')
        tarinfo = tarfile.TarInfo(name="README")
        tarinfo.size = len(inputStream.getbuffer())
        tar.addfile(tarinfo, inputStream)
        tar.close()
        self.outputStream.seek(0)

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
