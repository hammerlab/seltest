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
  -d NAME --driver NAME          Driver/Browser to run with. Can be one of
                                 chrome, firefox. Defaults to firefox.
  --firefox-path                 Path to Firefox binary, if you don't want to
                                 use the default.
  -o PATH --output PATH          Path where images will be saved; default is <path>.
  --config                       Path to config file. Default is to first look
                                 at ./.seltestrc, and then ~/.seltestrc
  --list-config                  Print out the current configuration being used.
  --wait SECONDS                 Wait SECONDS between each test. Useful for
                                 debugging tests and manually monitoring them.
                                 Defaults to 0.
"""
import __init__ as seltest

import docopt

import importlib
import os
import re
from selenium import webdriver
import sys


DEFAULTS = {
    '--driver': 'firefox'
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
            instance_of_base = isinstance(val, seltest.BaseMeta)
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
        print('Using default Python REPL: recommend downloading IPython'
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

    args = docopt.docopt(__doc__, version=seltest.__version__)

    config_path = args['--config'] or _find_config()
    config = {}
    if config_path:
        config_path = _expand_path(config_path)
        # allow_no_value so we can write `-v`, not `-v=True`
        cp = ConfigParser(allow_no_value=True)
        cp.read(config_path)
        # this allows -v to mean -v=True, not -v=None
        config = dict((key, True if value is None else value)
                      for key, value in cp.items('arguments'))

    config = _merge_config_dicts(DEFAULTS, config)
    config = _merge_config_dicts(args, config)
    return config


def _create_driver(args):
    driver = args['--driver'].lower()
    if driver == 'chrome':
        options = webdriver.ChromeOptions()
        options.add_extension(seltest.CHROME_EXT_PATH)
        driver = webdriver.Chrome(chrome_options=options)
    elif driver == 'firefox':
        profile = webdriver.FirefoxProfile()
        profile.add_extension(seltest.FIREFOX_EXT_PATH)
        profile.set_preference('app.update.auto', False)
        binary = None
        if args['--firefox-path']:
            binary = webdriver.firefox.firefox_binary.FirefoxBinary(
                _expand_path(args['--firefox-path']))
            driver = webdriver.Firefox(
                firefox_profile=profile, firefox_binary=binary)
        else:
            driver = webdriver.Firefox(firefox_profile=profile)
    else:
        print('No driver with name {}, try chrome or firefox.'.format(driver))
        sys.exit(1)
    return driver


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


def main(args=None):
    if args is None:
        args = _get_args()

    if args['--list-config']:
        _list_config(args)
        sys.exit(0)

    passes = True

    driver = None
    if not args['list']:
        driver = _create_driver(args)

    if args['interactive']:
        _start_interactive_session(driver)
    else:
        classes = _get_filtered_classes_to_run(args)
        image_path = _get_image_output_path(args)
        if not args['list'] and args['-v']:
            print('Saving images to {}'.format(image_path))
        if args['test']:
            print 'Running tests...'
            for Test in classes:
                print(' for {}'.format(Test.__name__))
                passes = Test(driver).run(image_dir=image_path,
                                          wait=args['--wait'])
        elif args['update']:
            print 'Updating images...'
            for Test in classes:
                print(' for {}'.format(Test.__name__))
                Test(driver).update(image_dir=image_path, wait=args['--wait'])
        elif args['list']:
            print 'All matched tests:'
            for Test in classes:
                methods = Test.__test_methods
                print(' {}: {} tests'.format(Test.__name__, len(methods)))
                for test in methods:
                    print('   {}'.format(test.__name))
                    if args['-v'] and test.__doc__:
                        print('     "{}"').format(test.__doc__)

    if driver:
        driver.quit()

    if passes:
        sys.exit(0)
    else:
        sys.exit('ERROR: some tests failed')


if __name__ == '__main__':
    main(_get_args())
