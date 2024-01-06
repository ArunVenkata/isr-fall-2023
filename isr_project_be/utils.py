import hashlib
import mimetypes
import os
import string
from elasticsearch.exceptions import RequestError
from .settings import es
from elasticsearch.helpers import bulk
# from transformers import TFAutoModelForQuestionAnswering, AutoTokenizer
from transformers import BertTokenizer, TFBertForQuestionAnswering
import tensorflow as tf
import fitz
import nltk

# nltk.download("punkt")

def sentence_tokenize(text):
    return nltk.sent_tokenize(text)

def get_document(index, filters=None):
    """
    Retrieve a document from Elasticsearch with optional filters.

    Parameters:
    - es: Elasticsearch client instance
    - index: Index name
    - filters: Filters as a dictionary (optional), including document ID

    Returns:
    - The retrieved document as a dictionary
    - None if the document is not found or an error occurs
    """
    try:
        # Construct the query with optional filters
        query = {'query': {'bool': {'must': []}}}
        if filters:
            if 'id' in filters:
                # Include document ID in the query
                query['query']['bool']['must'].append({'match': {'_id': filters.pop('id')}})
            query['query']['bool']['filter'] = filters

        result = es.search(index=index, body=query)
        
        # Check if any matching documents are found
        if result['hits']['total']['value'] > 0:
            return result['hits']['hits'][0]['_source']
        else:
            return None
    except RequestError as e:
        print(f"Request error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def is_pdf(filename):
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type == "application/pdf"



def add_qa_record(question, answer):

    # Define the index name
    index_name = 'qas'

    # Document to be added
    document = {
        'question': question,
        'answer': answer
    }

    # Index the document
    result = es.index(index=index_name, body=document)

    # Retrieve the added record
    added_record = es.get(index=index_name, id=result['_id'])

    return added_record



def get_unique_filename(folder, filename):
    base, extension = os.path.splitext(filename)
    counter = 1
    while os.path.exists(os.path.join(folder, filename)):
        filename = f"{base} ({counter}){extension}"
        counter += 1
    return filename


def register_checksum(checksum):
    es.index(index="files", body={"checksum": checksum})


def file_uploaded(file):
    # Check if the file has already been uploaded by querying Elasticsearch
    file_checksum = calculate_checksum(file)
    query = {"query": {"term": {"checksum": file_checksum}}}
    result = es.search(index="files", body=query)

    return result['hits']['total']['value'] > 0, file_checksum

def calculate_checksum(file):
    hasher = hashlib.sha256()
    current_seek = file.tell()
    file.seek(0)
    for chunk in iter(lambda: file.read(4096), b''):
        hasher.update(chunk)
    file.seek(current_seek)
    return hasher.hexdigest()


def get_answers_from_all_documents(model, tokenizer,user_question, n_results=10):
    """
    Given a question, retrieve and rank answers from all documents in an Elasticsearch index.

    Parameters:
    - user_question (str): The user's question.
    - index_name (str): The name of the Elasticsearch index.
    - n_results (int): The number of results to retrieve.

    Returns:
    - answers (list of dicts): List of answers, each containing the answer text, document ID, and score.
    """
    # Fetch all documents from the Elasticsearch index
    all_documents = es.search(index="docfiles", body={"query": {"match_all": {}}}, size=n_results)['hits']['hits']

    # Use the same function to get answers from all documents
    return get_answers_from_documents(model, tokenizer, user_question, all_documents, n_results)

def index_documents(documents):
    """
    Index a list of documents into Elasticsearch.

    Parameters:
    - documents (list of dicts): List of documents, where each document is a dictionary with keys like 'text'.
    - index_name (str): The name of the Elasticsearch index.

    Returns:
    - success (int): The number of documents successfully indexed.
    - failed (int): The number of documents that failed to index.
    """
    actions = [
        {
            "_op_type": "index",
            "_index": "docfiles",
            "_source": {"text": doc['text']}
        }
        for doc in documents
    ]

    success, failed = bulk(es, actions, raise_on_error=True)
    print(f"Indexed {success} documents successfully.")

    return success, failed


def get_qa_model():
    model_name_or_path = "bert-large-uncased"
    model_path = os.path.join(model_name_or_path, "config.json")
    if os.path.exists(model_path):
        model = TFBertForQuestionAnswering.from_pretrained(model_name_or_path)
        tokenizer = BertTokenizer.from_pretrained(model_name_or_path)
        print("Model loaded from local cache.")
        return model, tokenizer
    model = TFBertForQuestionAnswering.from_pretrained(model_name_or_path)
    tokenizer = BertTokenizer.from_pretrained(model_name_or_path)
    model.save_pretrained(model_name_or_path)
    tokenizer.save_pretrained(model_name_or_path)
    print("Model downloaded and cached locally.")
    return model, tokenizer

# # Example usage:
# cached_model, cached_tokenizer = get_qa_model()


def get_answers_from_documents(model, tokenizer, user_question, documents, n_results=10, max_chunk_size=512, overlap=128):
    """
    Given a question and a list of documents, retrieve and rank answers.

    Parameters:
    - user_question (str): The user's question.
    - documents (list of dicts): List of documents, where each document is a dictionary with keys like 'id' and 'text'.
    - n_results (int): The number of results to retrieve.
    - max_chunk_size (int): Maximum number of tokens in each document chunk.

    Returns:
    - answers (list of dicts): List of answers, each containing the answer text, document ID, score, and relevant portion.
    """
    answers = []
    documents = [doc["_source"] for doc in documents]

    for document_id, document in enumerate(documents):
        doc_text = document["text"]
        # Split the document into sentences
        sentences = sentence_tokenize(doc_text)

        # Combine sentences into chunks of max_chunk_size
        chunks = []
        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_chunk_size:
                current_chunk += sentence + " "
            else:
                chunks.append(current_chunk.strip())
                current_chunk = sentence + " "

        if current_chunk:
            chunks.append(current_chunk.strip())
        # Split the document into overlapping chunks
        # chunks = [doc_text[i:i+max_chunk_size] for i in range(0, len(doc_text), max_chunk_size - overlap)]

        for chunk_id, chunk_text in enumerate(chunks):
            inputs = tokenizer(user_question, chunk_text, return_tensors="tf", max_length=512, truncation=True)
            outputs = model(**inputs)

            start_logits_softmax = tf.nn.softmax(outputs.start_logits, axis=-1)
            end_logits_softmax = tf.nn.softmax(outputs.end_logits, axis=-1)

            # Extract answers based on token positions
            answer_start = tf.argmax(start_logits_softmax, axis=1).numpy()[0]
            answer_end = tf.argmax(end_logits_softmax, axis=1).numpy()[0]

            # Get the relevant portion from the original text using offset_mapping
            start_char = tf.reduce_sum(tf.cast(inputs["attention_mask"][0][:answer_start], tf.int32)).numpy()
            end_char = tf.reduce_sum(tf.cast(inputs["attention_mask"][0][:answer_end], tf.int32)).numpy()

            answer_text = chunk_text[start_char:end_char]

            # Extend the answer to form a complete sentence
            while end_char < len(chunk_text) and chunk_text[end_char] not in string.punctuation:
                end_char += 1

            extended_answer = chunk_text[start_char:end_char]
            if chunk_text.strip():
                doc_url = f"http://localhost:5000/static/{document['document_name']}"
                score = float(tf.reduce_mean(start_logits_softmax * end_logits_softmax))
                answers.append({
                    "answer": extended_answer,
                    "document_id": document_id,
                    "score": score,
                    "relevant_portion": chunk_text,
                    "doc_url": f"http://localhost:5000/static/{document['document_name']}"
                })
                print(doc_url, f"score : {score}")

    sorted_answers = sorted(answers, key=lambda x: x["score"], reverse=True)
    # print(set(x['doc_url'] for x in sorted_answers[:n_results]))  
    return sorted_answers[:n_results]



def index_pdf_text(pdf_file, document_name):
    text = ""
    # Use PyMuPDF to extract text from the PDF
    with fitz.open(pdf_file) as pdf_document:
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            text += page.get_text()
    # return text
    # Index the extracted text and document name into Elasticsearch
    es.index(index="docfiles", body={"text": text, "document_name": document_name})