from setuptools import setup, find_packages

setup(
    name='MessageQueue',
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

    entry_points="""
        [paste.app_factory]
        client_agent = message.clientagent:make_client_agent
        post_office = notifserver.postoffice:make_post_office
        post_office_router = notifserver.postoffice:make_post_office_router
    """,

    test_suite = 'nose.collector',

    author="Ben Bangert",
    author_email="bbangert@mozilla.com",
    description="Message Queue server",
    keywords="message-queue notifications server messaging queue",
)
