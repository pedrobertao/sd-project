import docx
import re
import hashlib

def create_document(template_path, doc_type=None, topic=None, author=None, text=None, date=None, signature=None):
    document = docx.Document(template_path)
    for paragraph in document.paragraphs:
        if(doc_type!=None):
            paragraph.text = re.sub(r'__TYPE__', doc_type, paragraph.text)
        if(topic!=None):
            paragraph.text = re.sub(r'__TOPIC__', topic, paragraph.text)
        if(author!=None):
            paragraph.text = re.sub(r'__TEXT__', text, paragraph.text)
        if(text!=None):
            paragraph.text = re.sub(r'__AUTHOR__', author, paragraph.text)
        if(date!=None):
            paragraph.text = re.sub(r'__DATE__', date, paragraph.text)
        if(signature!=None):
            paragraph.text = re.sub(r'__SIGNATURE__', signature, paragraph.text)

    title = author+'-'+topic
    title = re.sub(' ','_',title)
    document.save('{}.docx'.format(title))


def encrypt_string(hash_string):
    sha_signature = \
        hashlib.sha256(hash_string.encode()).hexdigest()
    return sha_signature

def compare_signature(author, date, test_signature):
    valid_signature = encrypt_string(author + date)
    if(test_signature == valid_signature):
        return True
    else: False
