import io
import os

import requests


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

        return resp.content

    def getfile(self, container, filepath):

        auth_token = self.authenticate()

        resp = requests.get(f'{self.url}/{container}/{filepath}',
                            headers={'X-Auth-Token': auth_token},
                            stream=True)

        return io.BytesIO(resp.content)

    def delete_object(self, container, filepath):

        auth_token = self.authenticate()

        resp = requests.delete(f'{self.url}/{container}/{filepath}',
                               headers={'X-Auth-Token': auth_token})

        return resp.content

    def delete_container(self, container):

        auth_token = self.authenticate()

        resp = requests.delete(f'{self.url}/{container}',
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

        resp = requests.post(self.auth_url,
                             json=data,
                             headers={'Content-type': 'application/json'})

        return resp.json()['access']['token']['id']
