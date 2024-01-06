import os
from celery import shared_task

from .utils import index_pdf_text, register_checksum


@shared_task()
def process_upload_doc(file_path, filename, checksum):
    print(file_path, "RECEIVED")
    fpath = os.path.join(os.path.dirname(__file__), 'files', filename)
    print("FILE PATH", fpath)
    res = index_pdf_text(fpath, filename)
    register_checksum(checksum)
    return {"success": True, "message":"Test", "data": fpath}