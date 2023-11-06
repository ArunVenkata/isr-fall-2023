from flask import jsonify
from .settings import create_app
from .bg_tasks import *

app = create_app(__name__)
celery_app = app.extensions["celery"]





@app.route("/", methods=["GET"])
def base_route():

    return jsonify({"success": True})
