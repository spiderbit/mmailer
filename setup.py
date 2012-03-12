#!/usr/bin/env python

import versioneer
versioneer.versionfile_source = 'mmail/_version.py'
versioneer.versionfile_build = 'mmail/_version.py'
versioneer.tag_prefix = ''
versioneer.parentdir_prefix = 'mmailer-'
import os

#from setuptools import setup
from distutils.core import setup


setup(name='mmailer',
			version=versioneer.get_version(),
			cmdclass=versioneer.get_cmdclass(),
			description='Serial/Mass mail tool',
			author='Stefan Huchler',
			author_email='s.huchler@gmail.com',
			url='https://github.com/spiderbit/mmailer',
			license='LICENSE',
			long_description=open('README').read(),
			packages = ['mmail'],
			scripts=['mmailer']
			)
