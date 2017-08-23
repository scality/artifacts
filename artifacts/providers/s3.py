import subprocess
import tarfile
import tempfile
import boto3


def extract(fileobj, dir_path):
    with tarfile.open(fileobj=fileobj, mode='r:gz') as t:
        t.extractall(dir_path)


class S3():
    def __init__(self, endpoint_url=None):
        self.endpoint_url = endpoint_url

    def upload_archive(self, bucket, fileobj):
        with tempfile.TemporaryDirectory() as tmp_dir:
            endpoint_arg = f'endpoint_url={self.endpoint_url}' \
                           if self.endpoint_url else ''
            extract(fileobj, tmp_dir)
            output = subprocess.check_output([
                     'aws', 's3', 'sync', tmp_dir,
                     f's3://{bucket}/', endpoint_arg])

        return output

    def getfile(self, bucket, filepath):
        resp = boto3.resource('s3').Object(bucket, filepath).get()

        return resp['Body']
