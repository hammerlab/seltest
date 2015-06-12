from setuptools import setup, find_packages

try:
   import pypandoc
   description = pypandoc.convert('README.md', to='rst', format='md')
except (IOError, ImportError):
   description = ''


setup(name='seltest',
      version=__import__('seltest').__version__,
      description='A perceptual difference testing framework for writing the easiest, most comprehensive tests you can run.',
      long_description=description,
      author='Isaac Hodes',
      author_email='isaachodes@gmail.com',
      url='https://github.com/ihodes/seltest/',
      packages=['seltest'],
      include_package_data=True,
      install_requires=['selenium',
                        'docopt',
                        'Pillow',
                        'flask',
                        'requests'],
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
