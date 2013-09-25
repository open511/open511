from flask import Flask, render_template, request
from lxml import etree
import requests

from validator import validate, Open511ValidationError

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
            doc_content = requests.get(url, headers={'Accept': 'application/xml, application/json;q=0.9'}).content
        elif 'doc_content' in request.form:
            doc_content = request.form['doc_content']
        elif 'upload' in request.files:
            doc_content = request.files['upload'].read()
        else:
            raise NotImplementedError
        doc = etree.fromstring(doc_content)
        doc_content = etree.tostring(doc, pretty_print=True)
        try:
            validate(doc)
            success = True
        except Open511ValidationError as e:
            success = False
            error = unicode(e)
        return render_template('validator.html', doc_content=doc_content, success=success, error=None if success else error)


if __name__ == '__main__':
    app.run(debug=True)