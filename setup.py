
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
			py_modules = ['versioneer'],
			classifiers=[
					'Development Status :: 5 - Production/Stable',
					'Environment :: Console',
					'Intended Audience :: End Users/Desktop',
					'Intended Audience :: Developers',
					'Intended Audience :: System Administrators',
					'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
					'Operating System :: MacOS :: MacOS X',
					'Operating System :: Microsoft :: Windows',
					'Operating System :: POSIX',
					'Programming Language :: Python',
					'Topic :: Communications :: Email',
					'Topic :: Office/Business',
					],
			scripts=['mmailer']
			)
