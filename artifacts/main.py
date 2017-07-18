from artifacts.providers import CloudFiles

from flask import Flask, request
artifact_flask = Flask(__name__)


api_endpoint = 'https://storage101.dfw1.clouddrive.com/v1'
tenant_id = 'MossoCloudFS_984990'
auth_url = 'https://https://identity.api.rackspacecloud.com/v2.0/tokens'
provider = CloudFiles(api_endpoint, tenant_id, auth_url)


@artifact_flask.route("/upload_archive/<container>", methods=['PUT'])
def upload_archive(container):

    provider.upload_archive(request.stream, container)

    return 'archive saved'


@artifact_flask.route("/getfile/<container>/<path:filepath>", methods=['GET'])
def getfile(filepath, container):

    f = provider.getfile(filepath, container)

    return f


if __name__ == "__main__":
    artifact_flask.run(host='0.0.0.0', debug=True, port=80)
