from flask import Flask, render_template, request
import requests

from converter import json_doc_to_xml, xml_to_json
from validator import validate, Open511ValidationError
from utils import deserialize, serialize

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def validator():
    if request.method == 'GET':
        return render_template('validator.html')
    elif request.method == 'POST':
        if 'url' in request.form:
            url = request.form['url']
            if not url.startswith('http'):
                url = 'http://' + url
            try:
                doc_content = requests.get(url, headers={'Accept': 'application/xml, application/json;q=0.9'}).content
            except Exception as e:
                return render_template('validator.html', fetch_error=unicode(e))
        elif 'doc_content' in request.form:
            doc_content = request.form['doc_content']
        elif 'upload' in request.files:
            doc_content = request.files['upload'].read()
        else:
            raise NotImplementedError
        try:
            if not isinstance(doc_content, unicode):
                doc_content = doc_content.decode('utf8')
            doc, doc_format = deserialize(doc_content)
        except Exception as e:
            return render_template('validator.html', doc_content=doc_content, deserialize_error=unicode(e))

        if doc_format == 'json':
            json_doc = doc
            try:
                xml_doc = json_doc_to_xml(json_doc, custom_namespace='http://validator.open511.com/custom-field')
            except Exception as e:
                return render_template('validator.html', error=unicode(e), doc_content=doc_content)
        elif doc_format == 'xml':
            xml_doc = doc
            try:
                json_doc = xml_to_json(xml_doc)
            except:
                pass
        else:
            raise NotImplementedError

        try:
            validate(xml_doc)
            success = True
        except Open511ValidationError as e:
            success = False
            error = unicode(e)
        return render_template('validator.html',
            success=success,
            error=None if success else error,
            xml_string=serialize(xml_doc),
            json_string=serialize(json_doc),
            doc_format=doc_format
        )


if __name__ == '__main__':
    app.run(debug=True)