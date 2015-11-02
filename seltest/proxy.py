"""
Reverse proxy requests to the server under test with injected JavaScript.

Used to inject JavaScript to instrument XHR requests so they can be tracked and
counted.
"""
from __future__ import absolute_import, unicode_literals, print_function
import re

from flask import Flask, request, Response, make_response
import requests


CHUNK_SIZE = 1024
HEAD_RE = re.compile('<head', re.I)
TRACKING_PENDING_REQUESTS_JS = b"""
<script>
window.__SELTEST_PENDING_REQUESTS = 0;
  var READY_STATE_DONE = 4,
      XHRSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.send = function() {
    window.__SELTEST_PENDING_REQUESTS++;
    this.addEventListener('readystatechange', function() {
      if (this.readyState === READY_STATE_DONE) {
        window.__SELTEST_PENDING_REQUESTS--;
      }
    }.bind(this), false);
    XHRSend.apply(this, arguments);
  };
</script>
"""

app = Flask(__name__.split('.')[0], static_url_path='/__SELTEST_AVOIDING_STATIC_URLS__')


HOST = None
def init(host):
    global HOST
    HOST = host
    return app


@app.route('/')
@app.route('/<path:url>')
def _reverse_proxy(url='/'):
    if not HOST:
        raise ValueError('URL has no host.'.format(url))

    url = 'http://{}/{}'.format(HOST, url)

    print('\n--------------\nURL: ', url,
          '\nHEADERS:\n', request.headers,
          '\n--------------')

    response = requests.get(url, stream=True, params=request.args)
    headers = dict(response.headers)

    # TODO: Only delete this if need be (e.g. if <head is in the first chunk of
    #       the response).
    if headers.get('content-length'):
        del headers['content-length']
    is_html_response = 'text/html' in headers.get('content-type')

    def resp_iter():
        is_first_chunk = True
        for chunk in response.iter_content(CHUNK_SIZE):
            # TODO: Possible bug: '<head' could span 2 chunks... (very unlikely)
            if is_first_chunk and is_html_response and _head_in_chunk(chunk):
                idx = HEAD_RE.search(chunk).start()
                yield chunk[:idx] + TRACKING_PENDING_REQUESTS_JS + chunk[idx:]
            else:
                yield chunk
            is_first_chunk = False
    return make_response((Response(resp_iter(),
                                   mimetype=headers.get('content-type')),
                          response.status_code,
                          headers))


def _head_in_chunk(chunk):
    return HEAD_RE.search(chunk) is not None


def _no_host(url):
    """Return True if there is no host in url."""
    return not url.startswith('localhost') or not '.' in url


if __name__ == '__main__':
    app.run('localhost', port=5050, debug=False)
