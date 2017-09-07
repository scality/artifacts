import collections
import io
import os

from providers import CloudFiles

from flask import abort, Flask, request, send_file, redirect
app = Flask(__name__)


api_endpoint = 'https://storage101.dfw1.clouddrive.com/v1'
tenant_id = 'MossoCloudFS_984990'
auth_url = 'https://identity.api.rackspacecloud.com/v2.0/tokens'
provider = CloudFiles(api_endpoint, tenant_id, auth_url)
universe = os.getenv('UNIVERSE')
artifacts_url = 'artifacts' if universe == 'prod' else f'artifacts-{universe}'


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


def find_container(provider, prefix, condition=''):
    if condition not in ['SUCCESSFUL', 'FAILED', '']:
        raise Exception('invalid condition (%s)' % condition)

    containers = [container for container in provider.list_containers()
                  if container.startswith(prefix)]
    containers.sort()

    for container in reversed(containers):
        if not condition:
            return container

        try:
            status = provider.getfile(container, '.final_status').content.decode()
        except Exception:
            status = 'INCOMPLETE'

        if condition == status:
            return container

    raise Exception("no matching containers")


@app.route("/latest/<container_prefix>", defaults={'filepath': ''})
@app.route("/latest/<container_prefix>/<path:filepath>")
def get_latest(container_prefix, filepath):
    try:
        container = find_container(provider, container_prefix)
    except Exception:
        abort(404)
    return redirect(
        f'https://{artifacts_url}.devsca.com/builds/{container}/{filepath}',
        code=302)


@app.route("/last_success/<container_prefix>", defaults={'filepath': ''})
@app.route("/last_success/<container_prefix>/<path:filepath>")
def get_last_success(container_prefix, filepath):
    try:
        container = find_container(provider, container_prefix, 'SUCCESSFUL')
    except Exception:
        abort(404)
    return redirect(
        f'https://{artifacts_url}.devsca.com/builds/{container}/{filepath}',
        code=302)


@app.route("/last_failure/<container_prefix>", defaults={'filepath': ''})
@app.route("/last_failure/<container_prefix>/<path:filepath>")
def get_last_failure(container_prefix, filepath):
    try:
        container = find_container(provider, container_prefix, 'FAILED')
    except Exception:
        abort(404)
    return redirect(
        f'https://{artifacts_url}.devsca.com/builds/{container}/{filepath}',
        code=302)


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=80)
