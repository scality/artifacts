import unittest
import os

import docker


class DockerTestCase(unittest.TestCase):

    def setUp(self):
        self.client = docker.from_env()

    def tearDown(self):
        for container in self.client.containers.list(all=True):
            container.remove(force=True)

        self.client.images.remove(image="artifacts")

    def test_container_build_and_run(self):

        pathToContainerDir = os.getcwd()
        artifacts_image = self.client.images.build(path=pathToContainerDir,
                                                   tag='artifacts')

        image_list = self.client.images.list()

        self.assertIn(artifacts_image, image_list)

        self.client.containers.run("artifacts", name='cloudfiles',
                                   detach=True, ports={80:80})

        cloudfiles_containter = self.client.containers.get("cloudfiles")
        container_list = self.client.containers.list()

        self.assertIn(cloudfiles_containter, container_list)
