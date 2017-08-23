import unittest
import tarfile

from .archive_stream import streamed_archive


class ArchiveStreamTestCase(unittest.TestCase):

    def test_streamed_archive(self):
        with tarfile.open(fileobj=streamed_archive('test_file', b'toto'),
                          mode='r:gz') as f:
            self.assertEqual(f.extractfile('test_file').read(), b'toto')
