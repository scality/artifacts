from artifacts.providers import CloudFiles

from flask import Flask, request
artifact_flask = Flask(__name__)


api_endpoint = 'https://storage101.dfw1.clouddrive.com'
tenant_id = 'MossoCloudFS_984990'
provider = CloudFiles(api_endpoint, tenant_id)


@artifact_flask.route("/upload_archive/<container_name>", methods=['PUT'])
def upload_archive(container_name):

    provider.upload_archive(request.stream, container_name)

    return 'archive saved'


@artifact_flask.route("/getfile/<path:filepath>", methods=['GET'])
def getfile(filepath):

    f = provider.getfile(filepath)

    return f.read()


if __name__ == "__main__":
    artifact_flask.run(host='0.0.0.0', debug=True, port=80)
