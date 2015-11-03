# coding=utf-8
__author__ = "Dmitry Zhiltsov"
__copyright__ = "Copyright 2015, Dmitry Zhiltsov"
__year__ = 2015

from setuptools import setup, find_packages


def readme():
    with open('README.md', 'r') as f:
        return f.read()


setup(
    name="devcentry.server.http",
    version="0.0.3",
    description="VCS HTTP server for devcentry",
    author="Dmitry Zhiltsov",
    author_email="dzhiltsov@me.com",
    long_description=readme(),
    url="https://github.com/zaabjuda/devcentry-vcs-http",
    package_dir={'': 'src'},
    packages=find_packages('src', exclude=('*.tests',)),
    include_package_data=True,
    zip_safe=False,
    namespace_packages=['devcentry', 'devcentry.server'],
    package_data={},
    install_requires=[
        "tornado==4.2.1",
        "PyYAML==3.11",
        "aiohttp==0.18.1",
    ],
    scripts=[
        'bin/devcentry_server.py',
    ],
    dependency_links=[
    ]
)
