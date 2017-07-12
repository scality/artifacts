#!/usr/bin/python

import unittest
import os
import shutil
import subprocess
import tarfile

from artifacts.providers import S3
from artifacts.main import untar_return_name, s3sync
from daemon import Daemon

s3 = S3()


class S3MockServer(Daemon):
    '''Start a daemonized s3 mock server'''

    # needs pip install moto[server] to work
    _start_cmd = ['moto_server', 's3']


class UntarTestCase(unittest.TestCase):

    # create testDir/testFile and testArchive.tar.gz
    def setUp(self):
        os.mkdir('testDir')

        with open('testDir/testFile', 'w+') as f:
            f.write('this is a test file')

        with tarfile.open('testArchive.tar.gz', 'w:gz') as arc:
            arc.add('testDir')

    def test_untar_return_name(self):
        archive_name = untar_return_name('testArchive.tar.gz')
        self.assertIn('testDir', os.listdir())
        self.assertEqual(archive_name, 'testDir')

    def tearDown(self):
        shutil.rmtree('testDir')
        os.remove('testArchive.tar.gz')


class S3SyncTestCase(unittest.TestCase):

    # start a s3 mock server
    @classmethod
    def setUpClass(self):
        self.mock_server = S3MockServer('s3mock')
        self.mock_server.start()

    def setUp(self):

        # create testDir/testFile
        os.mkdir('testDir')
        with open('testDir/testFile', 'w+') as f:
            f.write('this is a test file')

        # create a testBucket
        subprocess.check_output(['aws',
                                 's3',
                                 'mb',
                                 's3://testBucket',
                                 '--endpoint-url=http://localhost:5000'])

    def test_s3sync(self):
        s3sync('testDir', 'testBucket', 'http://localhost:5000')
        output = subprocess.check_output(['aws',
                                          's3',
                                          'ls',
                                          's3://testBucket/testDir/',
                                          '--endpoint-url=http://localhost:5000'])

        # output is in the form b'<date> <time> <filesize in bytes> <filename>/n'
        self.assertEqual(output[-9:-1], b'testFile')

    def tearDown(self):
        shutil.rmtree('testDir')

    # stop a s3 mock server
    @classmethod
    def tearDownClass(self):
        self.mock_server.stop()


if __name__ == '__main__':
    unittest.main()
