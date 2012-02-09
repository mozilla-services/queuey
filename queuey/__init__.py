# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import os

from pyramid.config import Configurator

from mozsvc.config import Config

from queuey.resources import Root
from queuey.storage import configure_from_settings


def main(global_config, **settings):
    config_file = global_config['__file__']
    config_file = os.path.abspath(
                    os.path.normpath(
                    os.path.expandvars(
                        os.path.expanduser(
                        config_file))))

    settings['config'] = config = Config(config_file)

    # Put values from the config file into the pyramid settings dict.
    for section in config.sections():
        setting_prefix = section.replace(":", ".")
        for name, value in config.get_map(section).iteritems():
            settings[setting_prefix + "." + name] = value

    config = Configurator(root_factory=Root, settings=settings)

    config.registry['backend_storage'] = configure_from_settings(
        'storage', settings['config'].get_map('storage'))
    config.registry['backend_metadata'] = configure_from_settings(
        'metadata', settings['config'].get_map('metadata'))

    # Load the application keys
    app_vals = settings['config'].get_map('application_keys')
    app_keys = {}
    for k, v in app_vals.items():
        for item in v:
            app_keys[item] = k
    config.registry['app_keys'] = app_keys

    # adds Mozilla default views
    config.include("mozsvc")

    # adds cornice
    config.include("cornice")

    config.scan('queuey.views')
    return config.make_wsgi_app()
