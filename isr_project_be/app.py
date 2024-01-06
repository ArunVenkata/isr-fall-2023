from flask import jsonify, request
from .settings import create_app
from .bg_tasks import *
from .utils import get_answers_from_all_documents, get_document, get_unique_filename, file_uploaded, is_pdf, register_checksum, add_qa_record, get_qa_model
from .settings import es
import os
import mimetypes
from werkzeug.utils import secure_filename

app = create_app(__name__)
celery_app = app.extensions["celery"]

model, tokenizer = get_qa_model()



@app.route("/", methods=["GET"])
def base_route():
    # res = add_qa_record("What is the meaning of life?", "The meaning of life is subjective and varies for each individual.")
    # print(res)
    index_name = "files"

    # Index settings and mappings (customize as needed)
    settings_body = {
        "index": {
            "blocks": {
                "read_only_allow_delete": None,
                "read_only": False
            }
        }
    }

    # index_settings = {
    #     "settings": {
    #         "number_of_shards": 1,
    #         "number_of_replicas": 0,  # Adjust replica settings as needed
    #     },
    #     "mappings": {
    #         "properties": {
    #             "checksum": {
    #                 "type": "keyword",
    #             },
    #             # Add other fields as needed
    #         }
    #     }
    # }
    # all_indices = es.indices.get_alias().keys()
    # print(all_indices)
    # es.delete_by_query(index=['files'], body={'query': {'match_all': {}}})
    # es.indices.delete(index=['files'])

    # es.indices.put_settings(index=index_name, body=settings_body)
    # es.indices.delete(index=["docfiles"], ignore=[400,404])
    # Create the index
    # es.indices.create(index=index_name, body=index_settings, ignore=400)
    return jsonify({"success": True})



# Define the folder to store files
@app.route('/upload', methods=['POST'])
def upload_file():
    # Limit maximum content length to 15MB
    max_content_length = 15 * 1024 * 1024
    if request.content_length > max_content_length:
        return jsonify({'success': False, 'message': 'File size exceeds maximum allowed (15MB)', 'data': {}}), 400

    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part', 'data': {}}), 400

    file = request.files['file']

    # Check if a file was submitted
    if not file or file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file', 'data': {}}), 400

    # Check if the file has an allowed MIME type
    if not is_pdf(file.filename):
        return jsonify({'success': False, 'message': 'Only PDF files are allowed', 'data': {}}), 400
    is_uploaded, checksum = file_uploaded(file)

    if is_uploaded:
            return jsonify({'success': False, 'message': 'File already uploaded', 'data': {}}), 400
    
    filename = secure_filename(file.filename)
    filename = get_unique_filename(app.config['UPLOAD_FOLDER'], filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    

    # process_upload_doc.delay(file_path=file_path, filename=filename)
    process_upload_doc.delay(file_path=file_path, filename=filename, checksum=checksum)
    
    file.close()

    return jsonify({'success': True, 'message': 'File uploaded successfully', 'data': {}}), 200







@app.route("/search", methods=["GET"])
def search():

    data = {}
    search_text = request.args.get("search", "")
    if not search_text:
        return jsonify({"success": False, "message": "Please enter something to search"}), 400
    res = get_answers_from_all_documents(model=model, tokenizer=tokenizer, user_question=search_text)
    return jsonify({"success": True, "data": res}), 200