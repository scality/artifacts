from providers import CloudFiles

from flask import Flask, request
app = Flask(__name__)


api_endpoint = 'https://storage101.dfw1.clouddrive.com/v1'
tenant_id = 'MossoCloudFS_984990'
auth_url = 'https://identity.api.rackspacecloud.com/v2.0/tokens'
provider = CloudFiles(api_endpoint, tenant_id, auth_url)


@app.route("/upload/<container>", methods=['PUT'])
def upload_archive(container):

    resp = provider.upload_archive(request.stream, container)

    return resp.content


@app.route("/getfile/<container>/<path:filepath>", methods=['GET'])
def getfile(filepath, container):

    f = provider.getfile(filepath, container)

    return f.content


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=80)
