#!/usr/bin/env python
from setuptools import setup

try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except(IOError, ImportError):
    long_description = ""

import requests_respectful

packages = [
    'requests_respectful',
]

requires = [
    'requests>=2.0.0',
    'redis',
    'PyYaml',
]

setup(
    name='requests-respectful',
    version=requests_respectful.__version__,
    description='Minimalist wrapper on top of Requests to work within rate limits of any amount of services simultaneously. Parallel processing friendly.',
    long_description=long_description,
    author=requests_respectful.__author__,
    author_email='info@nicholasbrochu.com',
    packages=packages,
    include_package_data=True,
    install_requires=requires,
    license='Apache License v2',
    url='https://github.com/nbrochu/requests-respectful',
    zip_safe=False,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5'
    ]
)
