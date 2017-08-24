import subprocess
import tarfile
import tempfile
import boto3


def extract(fileobj, dir_path):
    with tarfile.open(fileobj=fileobj, mode='r:gz') as t:
        t.extractall(dir_path)


class S3():
    def __init__(self, endpoint_url=None, bucket_name):
        self.endpoint_url = endpoint_url
        self.bucket_name = bucket_name
        self.s3 = boto3.resource('s3', endpoint_url=endpoint_url)

    def upload_archive(self, build_name, fileobj):
        endpoint_arg = f'--endpoint-url {endpoint_url}' if self.endpoint_url \
                                                        else ''
        with tempfile.TemporaryDirectory() as tmp_dir:
            extract(fileobj, tmp_dir)
            cmd = ['aws', 's3', 'sync', tmp_dir,
                   f's3://{self.bucket_name}/{build_name}/', endpoint_arg]
            response = subprocess.check_output(cmd)

        return response

    def getfile(self, bucket, filepath):
        response = self.s3.Object(bucket, filepath).get()

        return response['Body']

    def listing(self, build_name, filepath):
        full_path = build_name + '/' + filepath
        bucket = self.s3.Bucket(self.bucket_name)
        requested_list = bucket.objects.filter(Prefix=fullpath)

        return requested_list
