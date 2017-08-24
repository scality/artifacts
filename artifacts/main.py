import io
import os

from providers import CloudFiles

from flask import Flask, request, send_file, redirect
app = Flask(__name__)


api_endpoint = 'https://storage101.dfw1.clouddrive.com/v1'
tenant_id = 'MossoCloudFS_984990'
auth_url = 'https://identity.api.rackspacecloud.com/v2.0/tokens'
provider = CloudFiles(api_endpoint, tenant_id, auth_url)


@app.route("/upload/<container>", methods=['PUT'])
def upload_archive(container):

    resp = provider.upload_archive(container, request.stream)

    return resp.content


@app.route("/getfile/<container>/<path:filepath>", methods=['GET'])
def getfile(container, filepath):

    resp = provider.getfile(container, filepath)

    return send_file(io.BytesIO(resp.content),
                     attachment_filename=filepath.split('/')[-1])


@app.route("/builds/<path:filepath>", methods=['GET'])
def list_builds(filepath):
    universe = os.getenv('UNIVERSE')
    artifacts_url = 'artifacts' if universe == 'prod' else f'artifacts-{universe}'
    return redirect(f'https://{artifacts_url}.devsca.com/builds/{filepath}',
                    code=302)


@app.route("/delete_object/<container>/<path:filepath>", methods=['DELETE'])
def delete_object(container, filepath):

    resp = provider.delete_object(container, filepath)

    return resp.content


@app.route("/delete_container/<container>", methods=['DELETE'])
def delete_container(container):

    resp = provider.delete_container(container)

    return resp.content


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=80)
