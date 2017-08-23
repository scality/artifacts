from artifacts.providers.s3 import S3

from flask import Flask, request, send_file
app = Flask(__name__)


url = 'sreport.scality.com'
provider = S3(url)


@app.route("/upload/<bucket>", methods=['PUT'])
def upload_archive(bucket):

    resp = provider.upload_archive(bucket, request.stream)

    return resp


@app.route("/getfile/<bucket>/<path:filepath>", methods=['GET'])
def getfile(bucket, filepath):

    # resp is a fileobj
    resp = provider.getfile(bucket, filepath)

    return send_file(resp, attachment_filename=filepath.split('/')[-1])


@app.route("/builds", methods=['GET'])
def list_buckets(bucket, filepath):

    return 'lol'


@app.route("/delete_object/<bucket>/<path:filepath>", methods=['DELETE'])
def delete_object(bucket, filepath):

    resp = provider.delete_object(bucket, filepath)

    return resp


@app.route("/delete_bucket/<bucket>", methods=['DELETE'])
def delete_bucket(bucket):

    resp = provider.delete_bucket(bucket)

    return resp


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=80)
