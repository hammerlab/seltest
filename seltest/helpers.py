# -*- coding: utf-8 -*-

def url(url_str=''):
    """
    Decorator for specifying the URL the test shoudl visit, relative to the test
    class's `base_url`.
    """
    def decorator(method):
        method.__url = url_str
        return method
    return decorator


def waitfor(css_selector, text=None, classes=None):
    """
    Decorator for specifying elements (selected by a CSS-style selector) to
    explicitly wait for before taking a screenshot. If text is set, wait for the
    element to contain that text before taking the screenshot. If classes is
    present, wait until the element has all classes.
    """
    def decorator(method):
        if not isinstance(getattr(method, '__waitfors', None), list):
            setattr(method, '__waitfors', [])
        method.__waitfors.append({
            'css_selector': css_selector,
            'text': text,
            'classes': classes
        })
        return method
    return decorator


def dontwaitfor(css_selector):
    """
    Decorator for specifying elements that should not be waited for, if they're
    specified to be waited for in the class's `wait_for` or `wait_fors`
    attribute. Used to override the class setting.
    """
    def decorator(method):
        if not isinstance(getattr(method, '__dontwait', None), list):
            setattr(method, '__dontwait', [])
        method.__dontwait.append(css_selector)
        return method
    return decorator


def hide(css_selector):
    """
    Hides (by setting `el.hidden = true` in javascript) elements matching the
    selector. Useful for elements which may change from test to test and thus
    should be hidden.
    """
    def decorator(method):
        if not isinstance(getattr(method, '__hide', None), list):
            setattr(method, '__hide', [])
        method.__hide.append(css_selector)
        return method
    return decorator


def with_metaclass(mcls):
    """
    For metaclass compatibility between Python 2 and 3.

    cf. http://stackoverflow.com/questions/22409430/portable-meta-class-between-python2-and-python3
    """
    def decorator(cls):
        body = vars(cls).copy()
        # clean out class body
        body.pop('__dict__', None)
        body.pop('__weakref__', None)
        return mcls(cls.__name__, cls.__bases__, body)
    return decorator
