from flask import Flask
from celery import Celery, Task
import os
from dotenv import load_dotenv
from flask_cors import CORS, cross_origin

load_dotenv()

SETTINGS = {
    "PROJ_NAME": "isr_project_be.app",
    "REDIS_URL": os.getenv("REDIS_URL"),
    "CELERY": dict(
        broker_url = os.getenv("CELERY_BROKER_URL"),
        result_backend=os.getenv("CELERY_BACKEND_URL"),
        task_ignore_result=True,
    ),
    "UPLOAD_FOLDER": "files",
}
from elasticsearch import Elasticsearch

# Provide authentication credentials
es = Elasticsearch([os.getenv("ES_URI")], verify_certs=False, timeout=30,max_retries=10, retry_on_timeout=True)

def create_app(name):
    app = Flask(name,static_url_path="/static", static_folder='files')
    cors = CORS(app)
    app.config.from_mapping(SETTINGS)
    app.config.from_prefixed_env()
    celery_init_app(app)
    return app



def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app