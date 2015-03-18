"""
Seltest, the saltiest tests.

Usage:
  sel test [options] <path>
  sel update [options] <path>
  sel list [options] <path>
  sel interactive
  sel --version

Options:
  -h --help                      Show this screen.
  --version                      Show version.
  -v                             Verbose mode.
  -f FILTER --filter FILTER      Only operate on tests matching regexp FILTER.
                                 Can be a comma-separated list of names.
  -c NAME --classname NAME       Only operate on test classes named NAME.
                                 Can be a comma-separated list of names.
"""
import __init__ as seltest

import docopt

import importlib
import os
import re
import sys


def get_test_files(path):
    """
    Return list of python files starting with "test" on path.
    """
    files = [f for f in os.listdir(path)
             if os.path.isfile(os.path.join(path, f)) and f.startswith('test')
             and f.endswith('.py')]
    return files


def get_modules_from_files(path, filenames):
    """
    Return list of (imported) modules from list of filenames on path.
    """
    os.chdir(path)
    sys.path = ['.'] + sys.path
    return [importlib.import_module(m.split('.')[0]) for m in filenames]


def get_test_classes_from_modules(modules):
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


def filter_test_methods(cls, pred):
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


def get_test_classes_from_path(path):
    """Return list of test classes on path."""
    os.chdir(path)
    sys.path = ['.'] + sys.path
    files = get_test_files('.')
    modules = get_modules_from_files(path, files)
    classes = get_test_classes_from_modules(modules)
    return classes


def run_tests(test_classes):
    """Return result of all tests in the given test classes."""
    return [Test().run() for Test in test_classes]


def _get_args():
    return docopt.docopt(__doc__, version=seltest.__version__)


def main(args=None):
    if args is None:
        args = _get_args()

    if args['interactive']:
        print('Starting interactive browsing session...')
        from selenium import webdriver
        options = webdriver.ChromeOptions()
        options.add_extension(seltest.CHROME_EXT_PATH)
        driver = webdriver.Chrome(chrome_options=options)
        try:
            import IPython
            IPython.embed()
        except NameError:
            print('Using default Python REPL: recommend downloading IPython'
                  'for a better interactive experience')
            import code
            code.interact(local={'driver': driver})

    path = args['<path>']
    files = get_test_files(path)
    modules = get_modules_from_files(path, files)
    classes = get_test_classes_from_modules(modules)

    class_name_filters = args['--classname']
    if class_name_filters:
        class_name_filters = class_name_filters.split(',')
        class_name_res = [re.compile(p, re.I) for p in class_name_filters]
        classes = [c for c in classes
                   if any(f.search(c.__name__) for f in class_name_res)]
    test_name_filters = args['--filter']
    if test_name_filters:
        test_name_filters = test_name_filters.split(',')
        test_name_res = [re.compile(p, re.I) for p in test_name_filters]
        def pred(name):
            return any(f.search(name) for f in test_name_res)
        for cls in classes:
            cls = filter_test_methods(cls, pred)

    if args['test']:
        print 'Running tests...'
        for Test in classes:
            print(' for {}'.format(Test.__name__))
            Test().run(image_dir=os.getcwd())
    elif args['update']:
        print 'Updating images...'
        for Test in classes:
            print(' for {}'.format(Test.__name__))
            Test().update(image_dir=os.getcwd())
    elif args['list']:
        print 'All matched tests:'
        for Test in classes:
            methods = Test.__test_methods
            print(' {}: {} tests'.format(Test.__name__, len(methods)))
            for test in methods:
                print('   {}'.format(test.__name))
                if args['-v'] and test.__doc__:
                    print('     "{}"').format(test.__doc__)


if __name__ == '__main__':
    main(_get_args())
