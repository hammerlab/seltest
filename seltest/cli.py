# -*- coding: utf-8 -*-
"""
Seltest, the saltiest tests.

Usage:
  sel test [options] <path>
  sel update [options] <path>
  sel list [options] <path>
  sel interactive [options]
  sel --version

Options:
  -h --help                      Show this screen.
  --version                      Show version.
  -v                             Verbose mode.
  -f FILTER --filter FILTER      Only operate on tests matching regexp FILTER.
                                 Can be a comma-separated list of names.
  -c NAME --classname NAME       Only operate on test classes named NAME.
                                 Can be a comma-separated list of names.
  -b NAME --browser NAME         Browser to run with. Can be one of chrome,
                                 firefox, phantomjs, ie, safari, remote.
                                 Defaults to firefox.
  -o PATH --output PATH          Path where images will be saved.
                                 Default is <path>.
  --config                       Specify path to config file. Default is to first
                                 look for ./.seltestrc, and then ~/.seltestrc
  --config-profile NAME          Name of the profile to use. Inherits from the
                                 `default` profile.
  --config-list                  Print out the current configuration being used.
  --wait SECONDS                 Wait SECONDS between each test. Useful for
                                 debugging tests and manually monitoring them.
                                 Defaults to 0.
  --firefox-path PATH            Path to Firefox binary, if you don't want to
                                 use the default.
  --chrome-path PATH             Path to Chrome binary, if you don't want to
                                 use the default.
  --phantomjs-path PATH          Path to PhantomJS binary, if you don't want
                                 to use the default.
  --safari-path PATH             Path to Safari binary, if you don't want to
                                 use the default.
  --ie-path PATH                 Path to Interet Explorer binary, if you don't
                                 want to use the default.
  --remote-capabilities JSON     JSON describing the capabilities to be passed
                                 to the remote driver.
  --remote-command-executor URL  URL of the Selenium Remote Server to connect to.
"""
from __future__ import absolute_import, unicode_literals

import seltest
import seltest.proxy

import docopt

import importlib
import json
import multiprocessing
import os
import re
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import socket
import sys


DEFAULTS = {
    '--browser': 'firefox'
}


def _get_modules_from_path(path):
    """
    Return list of (imported) modules from list of filenames on path.
    """
    path = _expand_path(path)
    filenames = [f for f in os.listdir(path)
                 if os.path.isfile(os.path.join(path, f)) and f.startswith('test')
                 and f.endswith('.py')]
    sys.path = [path] + sys.path
    return [importlib.import_module(m.split('.')[0]) for m in filenames]


def _get_test_classes_from_modules(modules):
    """
    Return classes with metaclass seltest.seltest.BaseMeta in list of modules.
    """
    classes = []
    for module in modules:
        for attr in dir(module):
            val = getattr(module, attr)
            not_base_itself = not val == seltest.Base
            instance_of_base = (hasattr(val, '__bases__')
                                and seltest.Base in val.__bases__)
            if not_base_itself and instance_of_base:
                classes.append(val)
    return classes


def _filter_classes(classes, args):
    """
    Return list of classes. Given a list of classes args, return list of test
    classes to be run.
    """
    class_name_filters = args['--classname']
    if class_name_filters:
        class_name_filters = class_name_filters.split(',')
        class_name_res = [re.compile(p, re.I) for p in class_name_filters]
        classes = [c for c in classes
                   if any(f.search(c.__name__) for f in class_name_res)]
    return classes


def _filter_test_methods(cls, pred):
    """
    Return cls with test methods for which pred applied to its name returns
    True.

    Args:
      cls: a subclass of seltest.seltest.Base.
      pred: a function taking a string and returning True or False.
    """
    tests = cls.__test_methods
    filtered_tests = []
    for test in tests:
        name = test.__name
        if pred(name):
            filtered_tests.append(test)
    cls.__test_methods = filtered_tests
    return cls


def _filter_tests(classes, args):
    """
    Return list of classes. Given test classes and args, filters out tests in
    classes.
    """
    test_name_filters = args['--filter']
    if test_name_filters:
        test_name_filters = test_name_filters.split(',')
        test_name_res = [re.compile(p, re.I) for p in test_name_filters]
        def pred(name):
            return any(f.search(name) for f in test_name_res)
        for cls in classes:
            cls = _filter_test_methods(cls, pred)
    return classes


def _get_filtered_classes_to_run(args):
    """
    Return list of classes with all tests filtered out that don't match
    criteria.
    """
    path = _expand_path(args['<path>'])
    modules = _get_modules_from_path(path)
    classes = _get_test_classes_from_modules(modules)
    classes = _filter_classes(classes, args)
    classes = _filter_tests(classes, args)
    return classes


def _start_interactive_session(driver):
    print('Starting interactive browsing session...')
    print('(Use the `driver` variable to control the browser)')
    try:
        import IPython
        IPython.embed()
    except ImportError:
        print('Using default Python REPL: recommend downloading IPython '
              'for a better interactive experience')
        import code
        code.interact(local={'driver': driver})


def _expand_path(path):
    return os.path.expandvars(os.path.expanduser(path))


def _find_config():
    seltest_rc = '.seltestrc'
    local_config_path = os.path.join(os.getcwd(), seltest_rc)
    if os.path.exists(local_config_path):
        return local_config_path
    home_config_path = os.path.join(os.path.expanduser('~'), seltest_rc)
    if os.path.exists(home_config_path):
        return home_config_path


def _merge_config_dicts(dct1, dct2):
    """
    Return new dict created by merging two dicts, giving dct1 priority over
    dct2, but giving truthy values in dct2 priority over falsey values in dct1.
    """
    return {str(key): dct1.get(key) or dct2.get(key)
            for key in set(dct1) | set(dct2)}


def _get_args():
    try:  # py2
        from ConfigParser import ConfigParser
    except ImportError:  # py3
        from configparser import ConfigParser

    args = docopt.docopt(__doc__,
                         version=seltest.__version__,
                         argv=sys.argv[1:])

    config_path = args['--config'] or _find_config()
    config = {}
    profile_config = {}
    if config_path:
        config_path = _expand_path(config_path)
        # allow_no_value so we can write `-v`, not `-v=True`
        cp = ConfigParser(allow_no_value=True)
        cp.read(config_path)
        # this allows -v to mean -v=True, not -v=None
        config = dict((key, True if value is None else value)
                      for key, value in cp.items('default'))
        profile_name = args['--config-profile']
        if profile_name:
            profile_config = dict((key, True if value is None else value)
                                  for key, value in cp.items(profile_name))

    config = _merge_config_dicts(config, DEFAULTS)
    config = _merge_config_dicts(profile_config, config)
    config = _merge_config_dicts(args, config)
    return config


def _create_driver(args):
    config = {}
    browser = args['--browser'].lower()
    if browser == 'remote':
        if args['--remote-capabilities'] is None:
            sys.exit(
                'remote-capabilities must be present for the remote driver.')
        try:
            capabilities = json.loads(args['--remote-capabilities'])
        except ValueError:
            sys.exit(
                'Could not parse --remote-capabilities: make sure it is valid JSON')
        if args['--remote-command-executor'] is None:
            sys.exit(
                'remote browser must specify --remote-command-executor URL')
        config = {"command_executor": args['--remote-command-executor'],
                  "desired_capabilities": capabilities}
        driver = webdriver.Remote
    elif browser == 'chrome':
        if args['--chrome-path']:
            options = webdriver.ChromeOptions()
            options.binary_location = _expand_path(args['--chrome-path'])
            config['chrome_options'] = options
        driver = webdriver.Chrome
    elif browser == 'firefox':
        profile = webdriver.FirefoxProfile()
        profile.set_preference('app.update.auto', False)
        config['firefox_profile'] = profile
        if args['--firefox-path']:
            binary = webdriver.firefox.firefox_binary.FirefoxBinary(
                _expand_path(args['--firefox-path']))
            config['firefox_binary'] = binary
        driver = webdriver.Firefox
    elif browser == 'phantomjs':
        if args['--phantomjs-path']:
            config['executable_path'] = args['--phantomjs-path']
        driver = webdriver.PhantomJS
    elif browser == 'safari':
        if args['--safari-path']:
            config['executable_path'] = args['--safari-path']
        driver = webdriver.Safari
    elif browser == 'ie':
        if args['--ie-path']:
            config['executable_path'] = args['--ie-path']
        driver = webdriver.Ie
    else:
        msg = ('No driver with name {}, try one of chrome, firefox,'
               'phantomjs, safari, ie.')
        sys.exit(msg.format(browser))
    return driver(**config)


class RedirectStdStreams(object):
    # http://stackoverflow.com/questions/6796492/temporarily-redirect-stdout-stderr
    def __init__(self, stdout=None, stderr=None):
        self._stdout = stdout or sys.stdout
        self._stderr = stderr or sys.stderr

    def __enter__(self):
        self.old_stdout, self.old_stderr = sys.stdout, sys.stderr
        self.old_stdout.flush(); self.old_stderr.flush()
        sys.stdout, sys.stderr = self._stdout, self._stderr

    def __exit__(self, exc_type, exc_value, traceback):
        self._stdout.flush(); self._stderr.flush()
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr


def _start_reverse_proxy():
    # This socket business is to ensure we get a free port to bind to.
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    # Now we spin off our reverse proxy into another process, so that we can run
    # tests through it.
    def run_server(port):
        devnull = open(os.devnull, 'w')
        with RedirectStdStreams(stdout=devnull, stderr=devnull):
            seltest.proxy.app.run('localhost', port=port)
    p = multiprocessing.Process(target=run_server, args=(port,))
    p.start()
    return p, port


def _kill_reverse_proxy(p):
    p.terminate()


def _get_image_output_path(args):
    """
    Return the relative path in which the generated screnshots should be saved.
    """
    if args['--output']:
        path = _expand_path(args['--output'])
    else:
        path = _expand_path(args['<path>'])
    if not (os.path.isdir(path) and os.path.exists(path)):
        sys.exit('Image directory doesn\'t exist: {}'.format(path))
    return path


def _list_config(args):
    for key, val in args.iteritems():
        if key.startswith('--'):
            if val is True:
                print('{}'.format(key))
            if val is not None:
                print('{}={}'.format(key, val))


def _run(args, driver):
    if args['interactive']:
        _start_interactive_session(driver)
    else:
        classes = _get_filtered_classes_to_run(args)
        image_path = _get_image_output_path(args)
        if not args['list'] and args['-v']:
            print('Saving images to {}'.format(image_path))
        if args['test']:
            print('Running tests...')
            p, port = _start_reverse_proxy()
            for Test in classes:
                print(' for {}'.format(Test.__name__))
                passes = Test(driver)._run(image_dir=image_path,
                                           proxy_port=port,
                                           wait=args['--wait'])
            _kill_reverse_proxy(p)
            return passes
        elif args['update']:
            print('Updating images...')
            p, port = _start_reverse_proxy()
            for Test in classes:
                print(' for {}'.format(Test.__name__))
                Test(driver)._update(image_path, port,
                                     wait=args['--wait'])
            _kill_reverse_proxy(p)
        elif args['list']:
            print('All matched tests:')
            for Test in classes:
                methods = Test.__test_methods
                print(' {}: {} tests'.format(Test.__name__, len(methods)))
                for test in methods:
                    print('   {}'.format(test.__name))
                    if args['-v'] and test.__doc__:
                        print('     "{}"').format(test.__doc__)
    return True


def main(args=None):
    if args is None:
        args = _get_args()

    if args['--config-list']:
        _list_config(args)
        sys.exit(0)

    driver = None
    if not args['list']:
        driver = _create_driver(args)

    passes = False
    try:
        passes = _run(args, driver)
    finally:
        driver.quit()

    if passes:
        sys.exit(0)
    else:
        sys.exit('ERROR: some tests failed')


if __name__ == '__main__':
    main(_get_args())
