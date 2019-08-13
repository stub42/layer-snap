# Copyright 2016-2019 Canonical Ltd.
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

import os
import subprocess

from charmhelpers.core import hookenv
from charms import layer
from charms import reactive
from charms.reactive.helpers import any_file_changed, data_changed
from datetime import datetime, timedelta


def get_installed_flag(snapname):
    return 'snap.installed.{}'.format(snapname)


def get_disabled_flag(snapname):
    return 'snap.disabled.{}'.format(snapname)


def install(snapname, **kw):
    '''Install a snap.

    Snap will be installed from the coresponding resource if available,
    otherwise from the Snap Store.

    Sets the snap.installed.{snapname} flag.

    If the snap.installed.{snapname} flag is already set then the refresh()
    function is called.
    '''
    installed_flag = get_installed_flag(snapname)
    if reactive.is_flag_set(installed_flag):
        refresh(snapname, **kw)
    else:
        if hookenv.has_juju_version('2.0'):
            res_path = _resource_get(snapname)
            if res_path is False:
                _install_store(snapname, **kw)
            else:
                _install_local(res_path, **kw)
        else:
            _install_store(snapname, **kw)
        reactive.set_flag(installed_flag)

    # Installing any snap will first ensure that 'core' is installed. Set an
    # appropriate flag for consumers that want to get/set core options.
    core_installed = get_installed_flag('core')
    if not reactive.is_flag_set(core_installed):
        reactive.set_flag(core_installed)


def is_installed(snapname):
    return reactive.is_flag_set(get_installed_flag(snapname))


def refresh(snapname, **kw):
    '''Update a snap.

    Snap will be pulled from the coresponding resource if available
    and reinstalled if it has changed. Otherwise a 'snap refresh' is
    run updating the snap from the Snap Store, potentially switching
    channel and changing confinement options.
    '''
    # Note that once you upload a resource, you can't remove it.
    # This means we don't need to cope with an operator switching
    # from a resource provided to a store provided snap, because there
    # is no way for them to do that. Well, actually the operator could
    # upload a zero byte resource, but then we would need to uninstall
    # the snap before reinstalling from the store and that has the
    # potential for data loss.
    if hookenv.has_juju_version('2.0'):
        res_path = _resource_get(snapname)
        if res_path is False:
            _refresh_store(snapname, **kw)
        else:
            _install_local(res_path, **kw)
    else:
        _refresh_store(snapname, **kw)


def remove(snapname):
    hookenv.log('Removing snap {}'.format(snapname))
    subprocess.check_call(['snap', 'remove', snapname])
    reactive.clear_flag(get_installed_flag(snapname))


def connect(plug, slot):
    '''Connect or reconnect a snap plug with a slot.

    Each argument must be a two element tuple, corresponding to
    the two arguments to the 'snap connect' command.
    '''
    hookenv.log('Connecting {} to {}'.format(plug, slot), hookenv.DEBUG)
    subprocess.check_call(['snap', 'connect', plug, slot])


def connect_all():
    '''Connect or reconnect all interface connections defined in layer.yaml.

    This method will fail if called before all referenced snaps have been
    installed.
    '''
    opts = layer.options('snap')
    for snapname, snap_opts in opts.items():
        for plug, slot in snap_opts.get('connect', []):
            connect(plug, slot)


def disable(snapname):
    '''Disables a snap in the system

    Sets the snap.disabled.{snapname} flag

    This method doesn't affect any snap flag if requested snap does not
    exist
    '''
    hookenv.log('Disabling {} snap'.format(snapname))
    if not reactive.is_flag_set(get_installed_flag(snapname)):
        hookenv.log(
            'Cannot disable {} snap because it is not installed'.format(
                snapname), hookenv.WARNING)
        return

    subprocess.check_call(['snap', 'disable', snapname])
    reactive.set_flag(get_disabled_flag(snapname))


def enable(snapname):
    '''Enables a snap in the system

    Clears the snap.disabled.{snapname} flag

    This method doesn't affect any snap flag if requeted snap does not
    exist
    '''
    hookenv.log('Enabling {} snap'.format(snapname))
    if not reactive.is_flag_set(get_installed_flag(snapname)):
        hookenv.log(
            'Cannot enable {} snap because it is not installed'.format(
                snapname), hookenv.WARNING)
        return

    subprocess.check_call(['snap', 'enable', snapname])
    reactive.clear_flag(get_disabled_flag(snapname))


def restart(snapname):
    '''Restarts a snap in the system

    This method doesn't affect any snap flag if requested snap does not
    exist
    '''
    hookenv.log('Restarting {} snap'.format(snapname))
    if not reactive.is_flag_set(get_installed_flag(snapname)):
        hookenv.log(
            'Cannot restart {} snap because it is not installed'.format(
                snapname), hookenv.WARNING)
        return

    subprocess.check_call(['snap', 'restart', snapname])


def set(snapname, key, value):
    '''Changes configuration options in a snap

    This method will fail if snapname is not an installed snap
    '''
    hookenv.log('Set config {}={} for snap {}'.format(key, value, snapname))
    if not reactive.is_flag_set(get_installed_flag(snapname)):
        hookenv.log(
            'Cannot set {} snap config because it is not installed'.format(
                snapname), hookenv.WARNING)
        return

    subprocess.check_call(
        ['snap', 'set', snapname, '{}={}'.format(key, value)])


def set_refresh_timer(timer=''):
    '''Set the system refresh.timer option (snapd 2.31+)

    This method sets how often snapd will refresh installed snaps. Call with
    an empty timer string to use the system default (currently 4x per day).
    Use 'max' to schedule refreshes as far into the future as possible
    (currently 1 month). Also accepts custom timer strings as defined in the
    refresh.timer section here:
      https://forum.snapcraft.io/t/system-options/87

    This method does not validate custom strings and will lead to a
    CalledProcessError if an invalid string is given.

    :param: timer: empty string (default), 'max', or custom string
    '''
    if timer == 'max':
        # A month from yesterday is the farthest we should delay to safely stay
        # under the 1 month max. Translate that to a valid refresh.timer value.
        # Examples:
        # - Today is Friday the 13th, set the refresh timer to
        # 'thu2' (Thursday the 12th is the 2nd thursday of the month).
        # - Today is Tuesday the 1st, set the refresh timer to
        # 'mon5' (Monday the [28..31] is the 5th monday of the month).
        yesterday = datetime.now() - timedelta(1)
        dow = yesterday.strftime('%a').lower()
        # increment after int division because we want occurrence 1-5, not 0-4.
        occurrence = yesterday.day // 7 + 1
        timer = '{}{}'.format(dow, occurrence)

    # NB: 'system' became synonymous with 'core' in 2.32.5, but we use 'core'
    # here to ensure max compatibility.
    set(snapname='core', key='refresh.timer', value=timer)
    subprocess.check_call(['systemctl', 'restart', 'snapd.service'])


def get(snapname, key):
    '''Gets configuration options for a snap

    This method returns the stripped output from the snap get command.
    This method will fail if snapname is not an installed snap.
    '''
    hookenv.log('Get config {} for snap {}'.format(key, snapname))
    if not reactive.is_flag_set(get_installed_flag(snapname)):
        hookenv.log(
            'Cannot get {} snap config because it is not installed'.format(
                snapname), hookenv.WARNING)
        return

    return subprocess.check_output(['snap', 'get', snapname, key]).strip()


def get_installed_version(snapname):
    '''Gets the installed version of a snapname.
       This function will fail if snapname is not an installed snap.
    '''
    cmd = ['snap', 'info', snapname]
    hookenv.log('Get installed key for snap {}'.format(snapname))
    if not reactive.is_flag_set(get_installed_flag(snapname)):
        hookenv.log(
            'Cannot get {} snap installed version because it is not installed'
            .format(snapname), hookenv.WARNING)
        return
    return subprocess.check_output(cmd, encoding='utf-8').partition(
        'installed:')[-1].split()[0]


def get_installed_channel(snapname):
    '''Gets the tracking (channel) of a snapname.
       This function will fail if snapname is not an installed snap.
    '''
    cmd = ['snap', 'info', snapname]
    hookenv.log('Get channel for snap {}'.format(snapname))
    if not reactive.is_flag_set(get_installed_flag(snapname)):
        hookenv.log(
            'Cannot get snap tracking (channel) because it is not installed'
            .format(snapname), hookenv.WARNING)
        return
    return subprocess.check_output(cmd, encoding='utf-8').partition(
        'tracking:')[-1].split()[0]


def _snap_args(channel='stable', devmode=False, jailmode=False,
               dangerous=False, force_dangerous=False, connect=None,
               classic=False, revision=None):
    yield '--channel={}'.format(channel)
    if devmode is True:
        yield '--devmode'
    if jailmode is True:
        yield '--jailmode'
    if force_dangerous is True or dangerous is True:
        yield '--dangerous'
    if classic is True:
        yield '--classic'
    if revision is not None:
        yield '--revision={}'.format(revision)


def _install_local(path, **kw):
    key = 'snap.local.{}'.format(path)
    if (data_changed(key, kw) or any_file_changed([path])):
        cmd = ['snap', 'install']
        cmd.extend(_snap_args(**kw))
        cmd.append('--dangerous')
        cmd.append(path)
        hookenv.log('Installing {} from local resource'.format(path))
        subprocess.check_call(cmd)


def _install_store(snapname, **kw):
    """Install snap from store

    :param snapname: Name of snap to install
    :type snapname: str
    :param kw: Keyword arguments to pass on to ``snap install``
    :type kw: Dict[str, str]
    :raises: subprocess.CalledProcessError
    """
    cmd = ['snap', 'install']
    cmd.extend(_snap_args(**kw))
    cmd.append(snapname)
    hookenv.log('Installing {} from store'.format(snapname))
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                      universal_newlines=True)
        hookenv.log('Installation successful cmd="{}" output="{}"'
                    .format(cmd, out),
                    level=hookenv.DEBUG)
    except subprocess.CalledProcessError as cp:
        hookenv.log('Installation failed cmd="{}" returncode={} output="{}"'
                    .format(cmd, cp.returncode, cp.output),
                    level=hookenv.ERROR)
        raise


def _refresh_store(snapname, **kw):
    if not data_changed('snap.opts.{}'.format(snapname), kw):
        return

    # --amend allows us to refresh from a local resource
    cmd = ['snap', 'refresh', '--amend']
    cmd.extend(_snap_args(**kw))
    cmd.append(snapname)
    hookenv.log('Refreshing {} from store'.format(snapname))
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    print(out)


def _resource_get(snapname):
    '''Used to fetch the resource path of the given name.

    This wrapper obtains a resource path and adds an additional
    check to return False if the resource is zero length.
    '''
    res_path = hookenv.resource_get(snapname)
    if res_path and os.stat(res_path).st_size != 0:
        return res_path
    return False
