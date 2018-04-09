import datetime
import tarfile
import time
import requests
import os


class S3():

    def upload_archive(self, fileobj, url):
        pass

    def headfile(self):
        pass

    def getfile(self):
        pass

    def extract(self, archive_path, dirname):
        with tarfile.open(archive_path, 'r:gz') as a:
            a.extractall(dirname)


class CloudFiles():

    def __init__(self, api_endpoint, auth_url):
        self.url = api_endpoint.rstrip('/')
        self.auth_url = auth_url
        self.auth_token = None
        self.auth_token_expiration = None

    def upload_archive(self, container, fileobj):

        auth_token = self.authenticate()

        def feed():
            while True:
                chunk = fileobj.read(8192)
                if not chunk:
                    break
                yield chunk

        resp = requests.put(f'{self.url}/{container}',
                            data=feed(),
                            params={'extract-archive': 'tar.gz'},
                            headers={'X-Auth-Token': auth_token},
                            stream=True)

        return resp

    def headfile(self, container, filepath):

        auth_token = self.authenticate()

        resp = requests.head(f'{self.url}/{container}/{filepath}',
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

        now = datetime.datetime.utcfromtimestamp(time.time() - 60).isoformat()

        if not self.auth_token or now >= self.auth_token_expiration:
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

            token = resp.json()['access']['token']
            self.auth_token = token['id']
            self.auth_token_expiration = token['expires']

        return self.auth_token

    def listfiles(self, container, filepath, output_format):

        auth_token = self.authenticate()

        if output_format != "txt":
            url = f'{self.url}/{container}/?prefix={filepath}&delimiter=/'
        else:
            url = f'{self.url}/{container}/?prefix={filepath}'

        headers = {'X-Auth-Token': auth_token,
                   'Accept': "application/json"}

        resp = requests.get(url, headers=headers, stream=True)

        return resp
