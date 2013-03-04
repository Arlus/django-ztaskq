#!/usr/bin/env python
try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages
import django_ztaskq as distmeta

setup(
    version=distmeta.__version__,
    description=distmeta.__doc__,
    author=distmeta.__author__,
    author_email=distmeta.__contact__,
    url=distmeta.__homepage__,
    #   
    name='django-ztaskq',
    packages=find_packages(),
    install_requires=[
        'django-picklefield',
        'pyzmq',
        'pytz'
    ]   
)
