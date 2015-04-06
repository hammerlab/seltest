"""
Reverse proxy requests to the server under test with injected JavaScript.

Used to inject JavaScript to instrument XHR requests so they can be tracked and
counted.
"""
from __future__ import absolute_import, unicode_literals

from flask import Flask, request, Response, make_response
import requests


CHUNK_SIZE = 1024
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


app = Flask(__name__.split('.')[0], static_url_path='/__AVOIDING_STATIC_URLS__')

last_host_cache = None

@app.route('/')
@app.route('/<path:url>')
def _reverse_proxy(url='/'):
    global last_host_cache
    host, relative_url = _split_url(url)
    if not host:
        host = last_host_cache
    else:
        last_host_cache = host

    if not host:
        raise ValueError('URL has no host.'.format(url))

    url = 'http://{}/{}'.format(host, relative_url)
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
                idx = chunk.find(b'<head') or chunk.find(b'<HEAD')
                yield chunk[:idx] + TRACKING_PENDING_REQUESTS_JS + chunk[idx:]
            else:
                yield chunk
            is_first_chunk = False
    return make_response((Response(resp_iter(),
                                   mimetype=headers.get('content-type')),
                          response.status_code,
                          headers))


def _head_in_chunk(chunk):
    return b'<head' in chunk or b'<HEAD' in chunk


def _no_host(url):
    """Return True if there is no host in url."""
    return not url.startswith('localhost') or not '.' in url


def _split_url(url):
    splits = url.split('/')
    if splits[0].startswith('localhost'):
        return splits[0], '/'.join(splits[1:])
    elif '.' in splits[0]:
        return splits[0], '/'.join(splits[1:])
    else:
        return None, url


if __name__ == '__main__':
    app.run('localhost', port=5050, debug=True)
