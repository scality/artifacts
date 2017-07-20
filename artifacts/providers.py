import tarfile
import requests
import os

os.environ['RAX_LOGIN'] = 'release.engineering'
os.environ['RAX_PWD'] = 'Ap3u6iLKD9OU'


class Local():

    def upload_archive(self, fileobj, container):
        with tarfile.open(fileobj=fileobj, mode='r:gz') as a:
            a.extractall('/tmp/artifact/{}/'.format(container))

    def getfile(self, filepath, container):
        with open('/tmp/artifact/{}/{}'.format(container, filepath), 'r') as f:
            print(filepath)
            return f.read()


class S3():

    def upload_archive(self, fileobj, url):
        pass

    def getfile(self):
        pass

    def extract(self, archive_path, dirname):
        with tarfile.open(archive_path, 'r:gz') as a:
            a.extractall(dirname)


class CloudFiles():

    def __init__(self, api_endpoint, tenant_id, auth_url):
        self.url = '{}/{}'.format(api_endpoint, tenant_id)
        self.auth_url = auth_url

    def upload_archive(self, container, fileobj):

        auth_token = self.authenticate()
        resp = requests.put('{}/{}'.format(self.url, container),
                            data=fileobj,
                            params={'extract-archive': 'tar.gz'},
                            headers={'X-Auth-Token': auth_token})

        return resp.content

    def getfile(self, container, filepath):

        auth_token = self.authenticate()

        resp = requests.get('{}/{}/{}'.format(self.url,
                                              container,
                                              filepath),
                            headers={'X-Auth-Token': auth_token})

        return resp.content

    def delete_object(self, container, filepath):

        auth_token = self.authenticate()

        resp = requests.delete('{}/{}/{}'.format(self.url,
                                                 container,
                                                 filepath),
                               headers={'X-Auth-Token': auth_token})

        return resp.content

    def delete_container(self, container):

        auth_token = self.authenticate()

        resp = requests.delete('{}/{}'.format(self.url, container),
                               headers={'X-Auth-Token': auth_token})

        return resp.content

    def authenticate(self):
        data = {'auth':
                {'passwordCredentials':
                    {
                        'username': os.getenv('RAX_LOGIN'),
                        'password': os.getenv('RAX_PWD')
                    }
                 }
                }

        response = requests.post(self.auth_url,
                                 json=data,
                                 headers={'Content-type': 'application/json'})

        return response.json()['access']['token']['id']
