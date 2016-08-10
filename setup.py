from setuptools import setup, find_packages
import sys, os

version = '0.3.1'

install_requires=[
    'pyramid>=1.2dev',
    'raven>=5.20.0',
],

tests_require = [
    'WebTest >= 2.0.21',
    'mock >=2.0.0',
    ]

testing_extras = tests_require + [
    'nose',
    'coverage',
    ]

setup(name='pyramid_crow',
      version=version,
      description="http context compliant automatic raven integration for pyramid",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Nicholas Pilon',
      author_email='npilon@gmail.com',
      url='https://github.com/npilon/pyramid_crow',
      license='Apache 2.0',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=install_requires,
      extras_require={
          'testing': testing_extras,
      },
      tests_require=tests_require,
      )
