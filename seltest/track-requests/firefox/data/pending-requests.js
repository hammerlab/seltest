function trackRequests() {
  // Override send method of all XHR requests to count all pending requests.
  var pending_request_js = "\
  window.__SELTEST_PENDING_REQUESTS = 0;\
  var READY_STATE_DONE = 4,\
      XHRSend = XMLHttpRequest.prototype.send;\
\
  XMLHttpRequest.prototype.send = function() {\
    window.__SELTEST_PENDING_REQUESTS++;\
\
    this.addEventListener('readystatechange', function() {\
      if (this.readyState === READY_STATE_DONE) {\
        window.__SELTEST_PENDING_REQUESTS--;\
      }\
    }.bind(this), false);\
\
    XHRSend.apply(this, arguments);\
  };";
  var script = document.createElement("script");
  script.textContent = pending_request_js;
  document.documentElement.appendChild(script);
};

trackRequests();
