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
from os import uname
import shutil
import subprocess
from textwrap import dedent
import time

from charmhelpers.core import hookenv, host
from charms import layer
from charms import reactive
from charms.layer import snap
from charms.reactive import hook
from charms.reactive.helpers import data_changed


def install():
    opts = layer.options('snap')
    arch = uname()[4]
    for snapname, snap_opts in opts.items():
        supported_archs = snap_opts.pop('supported-architectures', None)
        if supported_archs and arch not in supported_archs:
            hookenv.log('Snap {} not supported on this architecture'.format(snapname))
            continue
        installed_state = 'snap.installed.{}'.format(snapname)
        if not reactive.is_state(installed_state):
            snap.install(snapname, **snap_opts)
    if data_changed('snap.install.opts', opts):
        snap.connect_all()


def refresh():
    opts = layer.options('snap')
    arch = uname()[4]
    for snapname, snap_opts in opts.items():
        supported_archs = snap_opts.pop('supported-architectures', None)
        if supported_archs and arch not in supported_archs:
            continue
        snap.refresh(snapname, **snap_opts)
    snap.connect_all()


@hook('upgrade-charm')
def upgrade_charm():
    refresh()


def get_series():
    return subprocess.check_output(['lsb_release', '-sc'],
                                   universal_newlines=True).strip()


def snapd_supported():
    # snaps are not supported in trusty lxc containers.
    if get_series() == 'trusty' and host.is_container():
        return False
    return True  # For all other cases, assume true.


def ensure_snapd():
    if not snapd_supported():
        hookenv.log('Snaps do not work in this environment', hookenv.ERROR)
        return

    # I don't use the apt layer, because that would tie this layer
    # too closely to apt packaging. Perhaps this is a snap-only system.
    if not shutil.which('snap'):
        cmd = ['apt', 'install', '-y', 'snapd']
        # LP:1699986: Force install of systemd on Trusty.
        if get_series() == 'trusty':
            cmd.append('systemd')
        subprocess.check_call(cmd, universal_newlines=True)

    # Work around lp:1628289. Remove this stanza once snapd depends
    # on the necessary package and snaps work in lxd xenial containers
    # without the workaround.
    if host.is_container() and not shutil.which('squashfuse'):
        cmd = ['apt', 'install', '-y', 'squashfuse', 'fuse']
        subprocess.check_call(cmd, universal_newlines=True)


def proxy_settings():
    proxy_vars = ('http_proxy', 'https_proxy', 'no_proxy')
    proxy_env = {key: value for key, value in os.environ.items()
                 if key in proxy_vars}

    snap_proxy = hookenv.config()['snap_proxy']
    if snap_proxy:
        proxy_env['http_proxy'] = snap_proxy
        proxy_env['https_proxy'] = snap_proxy
    return proxy_env


def update_snap_proxy():
    # This is a hack based on
    # https://bugs.launchpad.net/layer-snap/+bug/1533899/comments/1
    # Do it properly when Bug #1533899 is addressed.
    # Note we can't do this in a standard reactive handler as we need
    # to ensure proxies are configured before attempting installs or
    # updates.
    proxy = proxy_settings()

    path = '/etc/systemd/system/snapd.service.d/snap_layer_proxy.conf'
    if not proxy and not os.path.exists(path):
        return  # No proxy asked for and proxy never configured.

    if not data_changed('snap.proxy', proxy):
        return  # Short circuit avoids unnecessary restarts.

    if proxy:
        create_snap_proxy_conf(path, proxy)
    else:
        remove_snap_proxy_conf(path)
    subprocess.check_call(['systemctl', 'daemon-reload'],
                          universal_newlines=True)
    time.sleep(2)
    subprocess.check_call(['systemctl', 'restart', 'snapd.service'],
                          universal_newlines=True)


def create_snap_proxy_conf(path, proxy):
    host.mkdir(os.path.dirname(path))
    content = dedent('''\
                        # Managed by Juju
                        [Service]
                        ''')
    for proxy_key, proxy_value in proxy.items():
        content += 'Environment={}={}\n'.format(proxy_key, proxy_value)
    host.write_file(path, content.encode())


def remove_snap_proxy_conf(path):
    if os.path.exists(path):
        os.remove(path)


def ensure_path():
    # Per Bug #1662856, /snap/bin may be missing from $PATH. Fix this.
    if '/snap/bin' not in os.environ['PATH'].split(':'):
        os.environ['PATH'] += ':/snap/bin'


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
    hookenv.atstart(ensure_snapd)
    hookenv.atstart(ensure_path)
    hookenv.atstart(update_snap_proxy)
    hookenv.atstart(install)
    reactive._snap_registered = True
