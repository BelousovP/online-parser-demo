#!/usr/bin/env python

import sys
import os.path
import subprocess
import codecs
import json

from collections import defaultdict

import flask

# Name of JSON containing information on available DBs.
CORPORA_FILENAME = 'corpora.json'
CORPORA_LISTFILE = 'available_corpora.json'
# App settings. IMPORTANT: set DEBUG = False for publicly accessible
# installations, the debug mode allows arbitrary code execution.
DEBUG = True # TODO J
HOST = 'localhost'
#PORT = 80 # TODO J
PORT = 5042 # TODO J
STATIC_PATH = '/static'
LANG_PARAMETER = 'language'
USERDATA_PARAMETER = 'userdata'
PARSER_PATH = os.path.dirname(os.path.realpath(__file__))+'/parsers'
TEMPFILE_PATH = os.path.dirname(os.path.realpath(__file__))+'/tempfiles'
if not os.path.exists(TEMPFILE_PATH):
    os.mkdir(TEMPFILE_PATH)


# Template-related constants
INDEX_TEMPLATE = 'index.html'
RESULT_TEMPLATE = 'index.html'
SERVER_URL_PLACEHOLDER = '{{ SERVER_URL }}'
QUERY_PLACEHOLDER = '{{ QUERY }}'
LANGS_PLACEHOLDER = '{{ OPTIONS }}'
DB_PLACEHOLDER = '{{ DBNAME }}'
LANG_PLACEHOLDER = '{{ LANGUAGE }}'
CONTENT_START = '<!-- CONTENT-START -->'
CONTENT_END = '<!-- CONTENT-END -->'
ERROR_PLACEHOLDER = '{{ ERROR }}'

# Visualization wrapping
visualization_start = '<pre><code class="conllu">'
visualization_end = '</code></pre>'

def server_url(host=HOST, port=PORT):
    url = host#:%d' % (host, port) # TODO J 
    url = host+':%d' % (port) # TODO J 
    if not url.startswith('http://'):
        url = 'http://' + url # TODO do this properly
    return url

def load_corpora(filename=CORPORA_FILENAME):
    try:
        with open(filename) as f:
            return json.loads(f.read())
    except Exception, e:
        print 'Failed to load data on corpora from', filename
        raise

def load_corpora_list(filename=CORPORA_LISTFILE):

    try:
        with open(filename) as f:
            return json.loads(f.read())
    except Exception, e:
        print 'Failed to load data on corpora from', filename
        raise

def get_database_directory(dbname):
    return load_corpora().get(dbname, '')


def parse(language, texthash):
    script_dir = os.path.join(PARSER_PATH,language)

    command = 'cat %s.txt | ./parser_wrapper.sh'%(os.path.join(TEMPFILE_PATH,texthash))
    print command

    args = [command]
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (out, err) = p.communicate()
    return out, err


def get_index(fn=INDEX_TEMPLATE):
    with codecs.open(fn, encoding='utf-8') as f:
        return f.read()

def get_template(fn=RESULT_TEMPLATE):
    with codecs.open(fn, encoding='utf-8') as f:
        return f.read()

def render_languages(selected):
    corpora = load_corpora_list()
    print corpora
    options = []
    for name in corpora:
        s = ' selected="selected"' if name == selected else ''
        options.append('<option value="%s"%s>%s</option>' % (name, s, name))
    return '\n'.join(options)

def fill_template(template, content='', error='', language='', text=''): ## J: content=parsed data
    # TODO: use jinja

    assert CONTENT_START in template
    assert CONTENT_END in template
    header = template[:template.find(CONTENT_START)]
    trailer = template[template.find(CONTENT_END):]
    print type(header), type(content), type(trailer)
    filled = header + content + trailer
    filled = filled.replace(SERVER_URL_PLACEHOLDER, server_url())
    #t_q = query[:]
    #t_q = t_q.replace('"', '&quot;')
    #filled = filled.replace(QUERY_PLACEHOLDER, t_q)
    filled = filled.replace(LANGS_PLACEHOLDER, render_languages(language))
    filled = filled.replace(LANG_PLACEHOLDER, language)
    if len(error) < 1:
        filled = filled.replace(ERROR_PLACEHOLDER, '')
    else:
        filled = filled.replace(ERROR_PLACEHOLDER, '<div style="background-color:black; color:white; padding:20px;"><p>' + error.decode('utf8') + '</p></div>')
    return filled

app = flask.Flask(__name__, static_url_path=STATIC_PATH)


def parse_and_fill_template(language, texthash):
    template = get_template()
    out,err = parse(language,texthash)
    
    visualizations = []
    for block in out.split('\n\n')[:-1]:
        block = block.decode('utf-8')
        visualizations.append(visualization_start +
                              block + '\n\n' +
                              visualization_end)
    return fill_template(template, ''.join(visualizations), '', language, texthash)





@app.route("/types/<db>")
def types(db):
    try:
        return _types(db)
    except Exception, e:
        import traceback
        return "Internal error: %s\n%s" % (str(e), traceback.format_exc())


@app.route("/test") ## J: testing @app.route
def test():
    return "Testing @app.route()"


def _root():
    language = flask.request.form.get(LANG_PARAMETER)
    text = flask.request.form[USERDATA_PARAMETER]

    print text, language

    if not text or not language:
        # missing info, just show index
        template = get_index()
        return fill_template(template,language=language)
    else:
        texthash=str(abs(hash(text))) ## TODO J
        fname = os.path.join(TEMPFILE_PATH,texthash+u".txt")
        with codecs.open(fname,u"wt",u"utf-8") as f:
            print >> f, text
        # non-empty query, search and display
        return parse_and_fill_template(language, texthash)

@app.route("/", methods=['GET', 'POST']) ## J: main, runs first
def root():
    try:
        return _root()
    except Exception, e:
        import traceback
        return "Internal error: %s\n%s" % (str(e), traceback.format_exc())




#### STYLING FILES ####

@app.route('/css/<path:path>')
def serve_css(path):
    return flask.send_from_directory('css', path)

@app.route('/js/<path:path>')
def serve_js(path):
    return flask.send_from_directory('js', path)

def print_debug_warning(out):
    print >> out, """
##############################################################################
#
# WARNING: RUNNING IN DEBUG MODE. NEVER DO THIS IN PRODUCTION, IT
# ALLOWS ARBITRARY CODE EXECUTION.
#
##############################################################################
"""

def main(argv):
    if not DEBUG:
        host='0.0.0.0'
    else:
        print_debug_warning(sys.stdout)
        host='127.0.0.1'
    app.run(host=host, port=PORT, debug=DEBUG, use_reloader=True)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
