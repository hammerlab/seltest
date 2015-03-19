from setuptools import setup, find_packages

try:
   import pypandoc
   description = pypandoc.convert('README.md', 'rst')
except (IOError, ImportError):
   description = ''


setup(name='seltest',
      version='0.0.36',
      description='A perceptual diff testing framework for the fastest comprehensive tests you can write and run.',
      long_description=description,
      author='Isaac Hodes',
      author_email='isaachodes@gmail.com',
      url='https://github.com/ihodes/seltest/',
      packages=['seltest'],
      include_package_data=True,
      package_data={'seltest': ['track-requests/chrome.crx',
                                'track-requests/firefoxtrack.xpi']},
      install_requires=['selenium',
                        'docopt'],
      entry_points={
          'console_scripts': [
             'sel = seltest.cli:main',
          ]
      },
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: Apache Software License',
          'Topic :: Utilities',
          'Topic :: Software Development :: Testing'
      ],
      keywords=[
          'pdiff',
          'testing',
          'perceptual'
      ]
)
