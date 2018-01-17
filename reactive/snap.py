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
from distutils.version import LooseVersion
import os.path
from os import uname
import shutil
import subprocess
import tempfile
from textwrap import dedent
import time

from charmhelpers.core import hookenv, host
from charmhelpers.core.hookenv import ERROR
from charmhelpers.fetch import add_source, apt_update, apt_install
from charmhelpers.fetch.archiveurl import ArchiveUrlFetchHandler
from charms import layer
from charms import reactive
from charms.layer import snap
from charms.reactive import hook
from charms.reactive.helpers import data_changed
import yaml


def install():
    opts = layer.options('snap')
    # supported-architectures is EXPERIMENTAL and undocumented.
    # It probably should live in the base layer, blocking the charm
    # during bootstrap if the arch is unsupported.
    arch = uname()[4]
    for snapname, snap_opts in opts.items():
        supported_archs = snap_opts.pop('supported-architectures', None)
        if supported_archs and arch not in supported_archs:
            # Note that this does *not* error. The charm will need to
            # cope with the snaps it requested never getting installed,
            # likely by doing its own check on supported-architectures.
            hookenv.log('Snap {} not supported on {!r} architecture'
                        ''.format(snapname, arch), ERROR)
            continue
        installed_state = 'snap.installed.{}'.format(snapname)
        if not reactive.is_state(installed_state):
            snap.install(snapname, **snap_opts)
    if data_changed('snap.install.opts', opts):
        snap.connect_all()


def refresh():
    opts = layer.options('snap')
    # supported-architectures is EXPERIMENTAL and undocumented.
    # It probably should live in the base layer, blocking the charm
    # during bootstrap if the arch is unsupported.
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


def _get_snapd_version():
    process = subprocess.run(
        ['snap', 'version'], check=True,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        universal_newlines=True
    )
    version_info = dict(line.split() for line in process.stdout.splitlines())
    return LooseVersion(version_info['snapd'])


def ensure_snapd_min_version(min_version):
    snapd_version = _get_snapd_version()
    if snapd_version < LooseVersion(min_version):
        # Temporary until LP:1735344 lands
        add_source('ppa:snappy-dev/image', fail_invalid=True)
        apt_update()
        apt_install('snapd')
        snapd_version = _get_snapd_version()
        if snapd_version < LooseVersion(min_version):
            hookenv.log(
                "Failed to install snapd >= {}".format(min_version), ERROR)


def known_stores():
    process = subprocess.run(
        ['snap', 'known', 'store'], check=True,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        universal_newlines=True
    )
    store_ids = set()
    # Skip signature of assertions
    for part in process.stdout.split('\n\n')[::2]:
        fields = yaml.safe_load(part)
        store_ids.add(fields['store'])
    return store_ids


def configure_snap_enterprise_proxy():
    enterprise_proxy_url = hookenv.config()['snap_proxy_url']
    if not enterprise_proxy_url:
        return  # No enterprise proxy desired
    if reactive.get_state('snap.enterprise_proxy.configured'):
        return  # Already done by us
    ensure_snapd_min_version('2.30')
    proxy_store_process = subprocess.run(
        ['snap', 'get', 'core', 'proxy.store'],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True)
    if proxy_store_process.returncode == 0:
        # We already have a store configured (probably by someone
        # else), bail out.
        return
    assertions_url = "{}/v2/auth/store/assertions".format(enterprise_proxy_url)
    handler = ArchiveUrlFetchHandler()
    with tempfile.TemporaryDirectory() as tmpdir:
        local_bundle = os.path.join(tmpdir, "assertions.bundle")
        handler.download(assertions_url, local_bundle)
        subprocess.run(
            ["snap", "ack", local_bundle], check=True, stdin=subprocess.DEVNULL
        )
    store_ids = known_stores()
    if len(store_ids) > 1:
        hookenv.log(
            "More than one ({}) store configured".format(len(store_ids)),
            hookenv.ERROR)
        return
    store_id = store_ids.pop()
    subprocess.run(
        ['snap', 'set', 'core', 'proxy.store={}'.format(store_id)], check=True,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        universal_newlines=True
    )
    reactive.set_state('snap.enterprise_proxy.configured')


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
    hookenv.atstart(configure_snap_enterprise_proxy)
    hookenv.atstart(install)
    reactive._snap_registered = True
