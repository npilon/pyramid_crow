from setuptools import setup, find_packages
import sys, os

version = '0.1'

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
      install_requires=[
          # -*- Extra requirements: -*-
          'pyramid>=1.2dev',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
