import collections
import io
import os

from providers import CloudFiles
from flask import (abort,
                   Flask,
                   request,
                   Response,
                   send_file,
                   redirect,
                   render_template,
                   url_for)
app = Flask(__name__)


universe = os.getenv('UNIVERSE')
tenant_id = 'MossoCloudFS_984990'
auth_url = 'https://identity.api.rackspacecloud.com/v2.0/tokens'
region = 'iad3' if universe == 'prod' else 'dfw1'
api_endpoint = f'https://snet-storage101.{region}.clouddrive.com/v1'
provider = CloudFiles(api_endpoint, tenant_id, auth_url)


class PrefixMiddleware(object):
    """Allow application to live both at root and on subpath.

    If the request contains a HTTP header Script-Name, use its
    value as the prefix for redirects.

    """
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        environ['SCRIPT_NAME'] = environ.get('HTTP_SCRIPT_NAME', '')
        return self.app(environ, start_response)

app.wsgi_app = PrefixMiddleware(app.wsgi_app)


@app.route("/upload/<container>", methods=['PUT'], strict_slashes=False)
def upload_archive(container):

    resp = provider.upload_archive(container, request.stream)

    if resp.status_code >= 400:
        abort(resp.status_code)

    mime_type = resp.headers['Content-Type']

    def generate():
        for chunk in resp.iter_content(8192):
            yield chunk

    return Response(generate(), mimetype=mime_type)


@app.route("/builds", defaults={'container': ''}, methods=['GET'])
@app.route("/builds/<container>", methods=['GET'])
def add_final_slash(container):

    query_string = request.query_string.decode()

    content_url = url_for('displaycontent')
    if container:
        redirect_url = f'{content_url}{container}/'
    else:
        redirect_url = f'{content_url}'

    if query_string:
        redirect_url = f'{redirect_url}?{query_string}'

    return redirect(
        redirect_url,
        code=302)


@app.route("/builds/", defaults={'container': '', 'filepath': ''},
           methods=['GET'])
@app.route("/builds/<container>/", defaults={'filepath': ''},
           methods=['GET'])
@app.route("/builds/<container>/<path:filepath>", methods=['GET'])
def displaycontent(container, filepath):

    if not filepath or filepath[-1] == '/':
        output_format = request.args.get('format')

        resp = provider.listfiles(container, filepath, output_format)

        if output_format != "txt":
            template_file = 'listing.html'
        else:
            template_file = 'listing.txt'

        return render_template(
            template_file,
            entries=resp.json(),
            prefix=filepath,
            builds_url=url_for('displaycontent'))
    else:
        resp = provider.getfile(container, filepath)

        if resp.status_code >= 400:
            abort(resp.status_code)

        mime_type = resp.headers['Content-Type']

        def generate():
            for chunk in resp.iter_content(8192):
                yield chunk

        return Response(generate(), mimetype=mime_type)


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

    resp = provider.listfiles("", "", None)

    containers = [container['name'] for container in resp.json()
                  if container['name'].startswith(prefix)]
    containers.sort()

    for container in reversed(containers):
        if not condition:
            return container

        try:
            status = provider.getfile(container,
                                      '.final_status').content.decode()
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
    content_url = url_for('displaycontent')
    if filepath:
        redirect_url = f'{content_url}{container}/{filepath}'
    else:
        redirect_url = f'{content_url}{container}'
    return redirect(
        redirect_url,
        code=302)


@app.route("/last_success/<container_prefix>", defaults={'filepath': ''})
@app.route("/last_success/<container_prefix>/<path:filepath>")
def get_last_success(container_prefix, filepath):
    try:
        container = find_container(provider, container_prefix, 'SUCCESSFUL')
    except Exception:
        abort(404)
    content_url = url_for('displaycontent')
    if filepath:
        redirect_url = f'{content_url}{container}/{filepath}'
    else:
        redirect_url = f'{content_url}{container}'
    return redirect(
        redirect_url,
        code=302)


@app.route("/last_failure/<container_prefix>", defaults={'filepath': ''})
@app.route("/last_failure/<container_prefix>/<path:filepath>")
def get_last_failure(container_prefix, filepath):
    try:
        container = find_container(provider, container_prefix, 'FAILED')
    except Exception:
        abort(404)
    content_url = url_for('displaycontent')
    if filepath:
        redirect_url = f'{content_url}{container}/{filepath}'
    else:
        redirect_url = f'{content_url}{container}'
    return redirect(
        redirect_url,
        code=302)


@app.route("/", methods=['GET'], strict_slashes=False)
def root():
    return redirect(
        url_for('displaycontent'),
        code=302)


@app.route("/healthz", methods=['GET'])
def healthz():
    return 'OK!'


if __name__ == "__main__":
    assert 'RAX_LOGIN' in os.environ
    assert 'RAX_PWD' in os.environ
    assert 'UNIVERSE' in os.environ
    app.run(host='0.0.0.0', debug=True, port=50000)
