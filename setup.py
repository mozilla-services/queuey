__version__ = '0.8'

import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.rst')) as f:
    CHANGES = f.read()

reqs = [
    'distribute',
    'nose',
]

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if not on_rtd:
    reqs.extend([
        'cdecimal',
        'colander',
        'gunicorn',
        'metlog-py',
        'mozsvc',
        'pycassa',
        'pyramid',
        'thrift',
        'ujson',
        'webtest',
        'zope.interface',
    ])
else:
    # Ensure if we *are* on RTD, we include the plugin we need
    reqs.extend([
        'sphinx_http_domain'
    ])

setup(
    name='queuey',
    description="RESTful Message Queue",
    version=__version__,
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
    ],
    keywords="message-queue notifications server messaging queue",
    author="Mozilla Foundation",
    author_email="bbangert@mozilla.com",
    url="http://queuey.readthedocs.org/",
    license="MPLv2.0",
    packages=find_packages(),
    test_suite="queuey.tests",
    include_package_data=True,
    zip_safe=False,
    tests_require=['pkginfo', 'Mock>=0.8rc2', 'nose', 'supervisor'],
    install_requires=reqs,
    entry_points="""
        [paste.app_factory]
        main = queuey:main
    """,

)
