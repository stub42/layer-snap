# Copyright 2016 Canonical Ltd.
#
# This file is part of the Snap layer for Juju.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
'''
charms.reactive helpers for dealing with Snap packages.
'''
import os.path
import subprocess
from textwrap import dedent

from charmhelpers.core import hookenv, host
from charms import layer
from charms import reactive
from charms.layer import snap
from charms.reactive import hook
from charms.reactive.helpers import data_changed


def install():
    opts = layer.options('snap')
    for snapname, snap_opts in opts.items():
        snap.install(snapname, **snap_opts)
    if data_changed('snap.install.opts', opts):
        snap.connect_all()


def refresh():
    opts = layer.options('snap')
    for snapname, snap_opts in opts.items():
        snap.refresh(snapname, **snap_opts)
    snap.connect_all()


@hook('upgrade-charm')
def upgrade_charm():
    refresh()


def update_snap_proxy():
    # This is a hack based on
    # https://bugs.launchpad.net/layer-snap/+bug/1533899/comments/1
    # Do it properly when Bug #1533899 is addressed.
    # Note we can't do this in a standard reactive handler as we need
    # to ensure proxies are configured before attempting installs or
    # updates.
    proxy = hookenv.config()['snap_proxy']
    if not data_changed('snap.proxy', proxy):
        return
    path = '/etc/systemd/system/snapd.service.d/snap_layer_proxy.conf'
    if proxy:
        create_snap_proxy_conf(path, proxy)
    else:
        remove_snap_proxy_conf(path)
    subprocess.check_call(['systemctl', 'daemon-reload'],
                          universal_newlines=True)


def create_snap_proxy_conf(path, proxy):
    host.mkdir(os.path.dirname(path))
    content = dedent('''\
                        # Managed by Juju
                        [Service]
                        Environment=http_proxy={}
                        Environment=https_proxy={}
                        ''').format(proxy, proxy)
    host.write_file(path, content.encode())


def remove_snap_proxy_conf(path):
    if os.path.exists(path):
        os.remove(path)


# Per https://github.com/juju-solutions/charms.reactive/issues/33,
# this module may be imported multiple times so ensure the
# initialization hook is only registered once. I have to piggy back
# onto the namespace of a module imported before reactive discovery
# to do this.
if not hasattr(reactive, '_snap_registered'):
    # We need to register this to run every hook, not just during install
    # and config-changed, to protect against race conditions. If we don't
    # do this, then the config in the hook environment may show updates
    # to running hooks well before the config-changed hook has been invoked
    # and the intialization provided an opertunity to be run.
    hookenv.atstart(hookenv.log, 'Initializing Snap Layer')
    hookenv.atstart(update_snap_proxy)
    hookenv.atstart(install)
    reactive._snap_registered = True
