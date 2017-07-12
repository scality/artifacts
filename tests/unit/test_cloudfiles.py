import unittest
import os

from artifacts.providers import CloudFiles

os.environ['RAX_LOGIN'] = 'release.engineering'
os.environ['RAX_PWD'] = 'Ap3u6iLKD9OU'
api_endpoint = 'https://storage101.dfw1.clouddrive.com'
tenant_id = 'MossoCloudFS_984990'

cf = CloudFiles(api_endpoint, tenant_id)


class CloudFilesTestCase(unittest.TestCase):

    def test_authenticate(self):
        token = cf.authenticate()

        self.assertEqual(len(token), 142)
