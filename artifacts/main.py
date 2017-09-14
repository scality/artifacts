import collections
import io
import os

from providers import CloudFiles

from flask import abort, Flask, request, send_file, redirect
app = Flask(__name__)


universe = os.getenv('UNIVERSE')
tenant_id = 'MossoCloudFS_984990'
auth_url = 'https://identity.api.rackspacecloud.com/v2.0/tokens'
region = 'iad3' if universe == 'prod' else 'dfw1'
api_endpoint = f'https://storage101.{region}.clouddrive.com/v1'
provider = CloudFiles(api_endpoint, tenant_id, auth_url)
artifacts_url = f'artifacts.{universe}-private.devsca.com'


@app.route("/upload/<container>/", methods=['PUT'])
def upload_archive(container):

    resp = provider.upload_archive(container, request.stream)

    return resp.content


@app.route("/builds/<container>", defaults={'filepath': ''}, strict_slashes=False)
@app.route("/builds/<container>/<path:filepath>", methods=['GET'])
def getfile(container, filepath):

    resp = provider.getfile(container, filepath)

    return send_file(io.BytesIO(resp.content),
                     attachment_filename=filepath.split('/')[-1])


#@app.route("/builds/<path:filepath>", methods=['GET'])
#def list_builds(filepath):
#    return redirect(f'https://{artifacts_url}/builds/{filepath}',
#                    code=302)


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
        f'https://{artifacts_url}/builds/{container}/{filepath}',
        code=302)


@app.route("/last_success/<container_prefix>", defaults={'filepath': ''})
@app.route("/last_success/<container_prefix>/<path:filepath>")
def get_last_success(container_prefix, filepath):
    try:
        container = find_container(provider, container_prefix, 'SUCCESSFUL')
    except Exception:
        abort(404)
    return redirect(
        f'https://{artifacts_url}/builds/{container}/{filepath}',
        code=302)


@app.route("/last_failure/<container_prefix>", defaults={'filepath': ''})
@app.route("/last_failure/<container_prefix>/<path:filepath>")
def get_last_failure(container_prefix, filepath):
    try:
        container = find_container(provider, container_prefix, 'FAILED')
    except Exception:
        abort(404)
    return redirect(
        f'https://{artifacts_url}/builds/{container}/{filepath}',
        code=302)


if __name__ == "__main__":
    assert 'RAX_LOGIN' in os.environ
    assert 'RAX_PWD' in os.environ
    assert 'UNIVERSE' in os.environ
    app.run(host='0.0.0.0', debug=True, port=50000)
