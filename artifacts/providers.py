import tarfile
import requests
import os


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
        self.url = f'{api_endpoint}/{tenant_id}'
        self.auth_url = auth_url

    def upload_archive(self, container, fileobj):

        auth_token = self.authenticate()
        resp = requests.put(f'{self.url}/{container}',
                            data=fileobj,
                            params={'extract-archive': 'tar.gz'},
                            headers={'X-Auth-Token': auth_token})

        return resp

    def getfile(self, container, filepath):

        auth_token = self.authenticate()

        resp = requests.get(f'{self.url}/{container}/{filepath}',
                            headers={'X-Auth-Token': auth_token},
                            stream=True)

        return resp

    def delete_object(self, container, filepath):

        auth_token = self.authenticate()

        resp = requests.delete(f'{self.url}/{container}/{filepath}',
                               headers={'X-Auth-Token': auth_token})

        return resp

    def delete_container(self, container):

        auth_token = self.authenticate()

        resp = requests.delete(f'{self.url}/{container}',
                               headers={'X-Auth-Token': auth_token})

        return resp

    def authenticate(self):
        data = {'auth':
                {'passwordCredentials':
                    {
                        'username': os.getenv('RAX_LOGIN'),
                        'password': os.getenv('RAX_PWD')
                    }
                 }
                }

        resp = requests.post(self.auth_url,
                             json=data,
                             headers={'Content-type': 'application/json'})

        return resp.json()['access']['token']['id']

    def listfiles(self, path):

        auth_token = self.authenticate()

        resp = requests.get(f'{self.url}/{path}',
                            headers={
                                'X-Auth-Token': auth_token,
                                'Accept': 'application/json'
                            },
                            stream=True)

        return resp.json()
