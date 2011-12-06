from setuptools import setup, find_packages

setup(
    name='queuey',
    version=0.8,
    packages=find_packages(),

    install_requires=[
        'distribute',
        'gunicorn',
        'nose',
        'pyramid',
        'webtest',
        'thrift',
        'pycassa',
    ],

    tests_requires=[
        'mock>=0.7.2'
    ],

    entry_points="""
        [paste.app_factory]
        main = queuey:main
    """,

    test_suite='nose.collector',

    author="Ben Bangert",
    author_email="bbangert@mozilla.com",
    description="Message Queue server",
    keywords="message-queue notifications server messaging queue",
)
