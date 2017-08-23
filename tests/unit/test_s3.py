import unittest
import tempfile
import io

import boto3
from moto import mock_s3

from tests.util.stream.archive_stream import streamed_archive
from artifacts.providers.s3 import S3, extract

s3 = S3()


class S3TestCase(unittest.TestCase):

    def test_extract(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            archive = streamed_archive('test_file', b'toto')
            extract(archive, tmp_dir)
            with open(f'{tmp_dir}/test_file', mode='rb') as f:
                content = f.read()

        assert content == b'toto'

    @mock_s3
    def test_extract_and_getfile(self):
        conn = boto3.resource('s3')
        conn.create_bucket(Bucket='test_bucket')

        conn.Bucket('test_bucket').upload_fileobj(io.BytesIO(b'toto'),
                                                  'test_file')
        filecontent = s3.getfile('test_bucket', 'test_file').read()

        assert filecontent == b'toto'
