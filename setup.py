from setuptools import setup, find_packages
import sys, os

version = '0.10'

setup(name='pymbt',
      version=version,
      description="Python MBT Library",
      long_description="",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Richard Harrison',
      author_email='rdharrison2@hotmail.co.uk',
      url='',
      license='',
      packages=find_packages(exclude=['test']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
              'networkx'
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      scripts=[],
      )
