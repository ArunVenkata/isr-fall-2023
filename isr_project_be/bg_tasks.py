from celery import shared_task




@shared_task()
def process_upload_doc():
    return {"success": True, "message":"Test"}