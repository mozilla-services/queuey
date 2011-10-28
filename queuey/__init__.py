# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla Message Queue
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
# Ben Bangert (bbangert@mozilla.com)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
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

    # adds cornice
    config.include("cornice")

    # adds Mozilla default views
    config.include("mozsvc")
    
    # adds ip auth
    config.include('pyramid_ipauth')

    config.scan('queuey.views')
    return config.make_wsgi_app()
