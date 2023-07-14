# -*- coding: utf-8 -*-
from distutils.core import setup
setup(
	name='pfl',
	version='3.2.1',
	author='Banana',
	author_email='mail@bananas-playground.net',
	description='Searchable online file/package database for Gentoo.',
	packages = ['pfl'],
	keywords='gentoo',
	license='GNU General Public License v2',
	classifiers=['Intended Audience :: Users',
		'Natural Language :: English',
		'Operating System :: GNU/Linux',
		'Programming Language :: Python :: 3.5',
		'License :: OSI Approved :: GNU General Public License v2',
		],
	scripts = ['bin/e-file', 'bin/pfl'],
	data_files = [('share/man/man1', ['man/pfl.1'])],
	)
