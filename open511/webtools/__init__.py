try:
    unicode
except NameError:
    unicode = str

import functools
import logging
import os

from flask import Flask, render_template, request, Response, make_response
import requests

from open511.converter import json_doc_to_xml, xml_to_json, FORMATS, FORMATS_LIST, open511_convert
from open511.validator import validate, Open511ValidationError
from open511.utils.serialization import deserialize, serialize

app = Flask(__name__)

if os.environ.get('OPEN511_EMAIL_ERRORS'):
    from logging.handlers import SMTPHandler
    if os.environ.get('MANDRILL_USERNAME'):
        # Automatically support Mandrill config
        mailhost = 'smtp.mandrillapp.com'
        mailport = 587
        username = os.environ.get('MANDRILL_USERNAME')
        password = os.environ.get('MANDRILL_APIKEY')
    else:
        mailhost = os.environ.get('SMTP_SERVER')
        mailport = int(os.environ.get('SMTP_SERVER_PORT', 25))
        username = os.environ.get('SMTP_USERNAME')
        password = os.environ.get('SMTP_PASSWORD')
    mail_config = dict(
        mailhost=(mailhost,mailport),
        fromaddr=os.environ.get('OPEN511_EMAIL_ERRORS_FROM', 'server-error@validator.open511.org'),
        toaddrs=[os.environ['OPEN511_EMAIL_ERRORS']],
        subject='Open511 Validator server error'
    )
    if username and password:
        mail_config['credentials'] = (username, password)
    mail_handler = SMTPHandler(**mail_config)
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)

if os.environ.get('SENTRY_DSN'):
    from raven.contrib.flask import Sentry
    sentry = Sentry(app, dsn=os.environ['SENTRY_DSN'])
 
def no_cache(f):
    def new_func(*args, **kwargs):
        resp = make_response(f(*args, **kwargs))
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
        return resp
    return functools.update_wrapper(new_func, f)

@app.route('/', methods=['GET', 'POST'])
@no_cache
def validator():
    ctx = {
        'conversion_formats': FORMATS_LIST
    }
    if request.method == 'GET' and 'url' not in request.args:
        return render_template('validator.html', **ctx)
    else:
        try:
            doc_content = _load_document()
        except FetchError as e:
            ctx['fetch_error'] = unicode(e)
            return render_template('validator.html', **ctx)
        try:
            if not isinstance(doc_content, unicode):
                doc_content = doc_content.decode('utf8')
            doc, doc_format = deserialize(doc_content)
        except Exception as e:
            ctx.update(doc_content=doc_content, deserialize_error=unicode(e))
            return render_template('validator.html', **ctx)

        if doc_format == 'json':
            json_doc = doc
            try:
                xml_doc = json_doc_to_xml(json_doc, custom_namespace='http://validator.open511.com/custom-field')
            except Exception as e:
                ctx.update(error=unicode(e), doc_content=doc_content)
                return render_template('validator.html', **ctx)
        elif doc_format == 'xml':
            xml_doc = doc
            try:
                json_doc = xml_to_json(xml_doc)
            except:
                json_doc = 'Error generating JSON'
        else:
            raise NotImplementedError

        try:
            validate(xml_doc)
            success = True
        except Open511ValidationError as e:
            success = False
            error = unicode(e)
        ctx.update(
            success=success,
            error=None if success else error,
            xml_string=serialize(xml_doc),
            json_string=serialize(json_doc),
            doc_format=doc_format
        )
        return render_template('validator.html', **ctx)

class FetchError(Exception):
    pass

def _load_document():
    if 'url' in request.values:
        url = request.values['url']
        if not url.startswith('http'):
            url = 'http://' + url
        try:
            doc_content = requests.get(url, headers={'Accept': 'application/xml, application/json;q=0.9'}).content
        except Exception as e:
            raise FetchError(unicode(e))
    elif 'doc_content' in request.form:
        doc_content = request.form['doc_content']
    elif 'upload' in request.files:
        doc_content = request.files['upload'].read()
    else:
        raise NotImplementedError
    return doc_content

@app.route('/convert', methods=['GET', 'POST'])
@no_cache
def convert():
    doc_content = _load_document()
    if not isinstance(doc_content, unicode):
        doc_content = doc_content.decode('utf8')
    doc, doc_format = deserialize(doc_content)

    format = request.values['format']
    result = open511_convert(doc, format)
    format_info = FORMATS[format]
    return Response(result, mimetype=format_info.content_type)

if __name__ == '__main__':
    app.run(debug=True)