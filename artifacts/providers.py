import tarfile
import requests
import os

os.environ['RAX_LOGIN'] = 'release.engineering'
os.environ['RAX_PWD'] = 'Ap3u6iLKD9OU'


class AbstractProvider():

    def upload_archive(self):
        pass

    def getfile(self):
        pass


class Local(AbstractProvider):

    def upload_archive(self, fileobj, container):
        with tarfile.open(fileobj=fileobj, mode='r:gz') as a:
            a.extractall('/tmp/artifact/{}/'.format(container))

    def getfile(self, filepath, container):
        with open('/tmp/artifact/{}/{}'.format(container, filepath), 'r') as f:
            print(filepath)
            return f.read()


class S3(AbstractProvider):

    def upload_archive(self, fileobj, url):
        pass

    def getfile(self):
        pass

    def extract(self, archive_path, dirname):
        with tarfile.open(archive_path, 'r:gz') as a:
            a.extractall(dirname)


class CloudFiles(AbstractProvider):

    def __init__(self, api_endpoint, tenant_id):
        self.url = '{}/v1/{}'.format(api_endpoint, tenant_id)

    def upload_archive(self, fileobj, container):

        auth_token = self.authenticate()
        resp = requests.put('{}/{}'.format(self.url, container),
                            data=fileobj,
                            params={'extract-archive': 'tar.gz'},
                            headers={'X-Auth-Token': auth_token})

        return resp.status_code

    def getfile(self, filepath, container):

        auth_token = self.authenticate()

        resp = requests.get('{}/{}/{}'.format(self.url, container, filepath),
                            params={'format': 'json'},
                            headers={'X-Auth-Token': auth_token})

        return resp.content

    def authenticate(self):
        data = {'auth':
                {'passwordCredentials':
                    {'username': os.getenv('RAX_LOGIN'),
                     'password': os.getenv('RAX_PWD')
                     }
                 }
                }

        auth_url = 'https://identity.api.rackspacecloud.com/v2.0/tokens'
        response = requests.post(auth_url,
                                 json=data,
                                 headers={'Content-type': 'application/json'})

        return response.json()['access']['token']['id']
