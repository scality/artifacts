from providers.s3 import S3

from flask import Flask, render_template
app = Flask(__name__)

url = 'sreport.scality.com'
provider = S3(url)


@app.route("/builds/", defaults={'bucket': None, 'filepath': None})
@app.route("/builds/<bucket>/<path:filepath>", methods=['GET'])
def listing(bucket, filepath):

    objects = provider.listing(bucket, filepath)

    return render_template('listing.html', objects)


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=80)
