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

import os
import subprocess

from charmhelpers.core import hookenv
from charms import layer
from charms import reactive
from charms.reactive.helpers import any_file_changed, data_changed


def install(snapname, **kw):
    '''Install a snap.

    Snap will be installed from the coresponding resource if available,
    otherwise from the Snap Store.

    Sets the snap.installed.{snapname} state.

    If the snap.installed.{snapname} state is already set and
    the snap options have been changed, then the refresh() function
    is called.
    '''
    installed_state = 'snap.installed.{}'.format(snapname)
    if reactive.is_state(installed_state):
        if data_changed('snap.opts.{}'.format(snapname), kw):
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
        reactive.set_state(installed_state)


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
    # is no way for them to do that.
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
    subprocess.check_call(['snap', 'remove', snapname],
                          universal_newlines=True)
    reactive.remove_state('snap.installed.{}'.format(snapname))


def connect(plug, slot):
    '''Connect or reconnect a snap plug with a slot.

    Each argument must be a two element tuple, corresponding to
    the two arguments to the 'snap connect' command.
    '''
    hookenv.log('Connecting {} to {}'.format(plug, slot), hookenv.DEBUG)
    subprocess.check_call(['snap', 'connect', plug, slot],
                          universal_newlines=True)


def connect_all():
    '''Connect or reconnect all interface connections defined in layer.yaml.

    This method will fail if called before all referenced snaps have been
    installed.
    '''
    opts = layer.options('snap')
    for snapname, snap_opts in opts.items():
        for plug, slot in snap_opts.get('connect', []):
            connect(plug, slot)


def _snap_args(channel='stable', devmode=False, jailmode=False,
               dangerous=False, force_dangerous=False, connect=None):
    if channel != 'stable':
        yield '--channel={}'.format(channel)
    if devmode is True:
        yield '--devmode'
    if jailmode is True:
        yield '--jailmode'
    if force_dangerous is True or dangerous is True:
        yield '--dangerous'


def _install_local(path, **kw):
    key = 'snap.local.{}'.format(path)
    if (data_changed(key, kw) or any_file_changed([path])):
        cmd = ['snap', 'install']
        cmd.extend(_snap_args(**kw))
        cmd.append('--dangerous')
        cmd.append(path)
        hookenv.log('Installing {} from local resource'.format(path))
        subprocess.check_call(cmd, universal_newlines=True)


def _install_store(snapname, **kw):
    cmd = ['snap', 'install']
    cmd.extend(_snap_args(**kw))
    cmd.append(snapname)
    hookenv.log('Installing {} from store'.format(snapname))
    # Per https://bugs.launchpad.net/bugs/1622782, we don't
    # get a useful error code out of 'snap install', much like
    # 'snap refresh' below.
    try:
        out = subprocess.check_output(cmd, universal_newlines=True,
                                      stderr=subprocess.STDOUT)
        print(out)
    except subprocess.CalledProcessError as x:
        print(x.output)
        if "already installed" not in x.output:
            raise


def _refresh_store(snapname, **kw):
    cmd = ['snap', 'refresh']
    cmd.extend(_snap_args(**kw))
    cmd.append(snapname)
    hookenv.log('Refreshing {} from store'.format(snapname))
    # Per https://bugs.launchpad.net/layer-snap/+bug/1588322 we don't get
    # a useful error code out of 'snap refresh'. We are forced to parse
    # the output to see if it is a non-fatal error.
    # subprocess.check_call(cmd, universal_newlines=True)
    try:
        out = subprocess.check_output(cmd, universal_newlines=True,
                                      stderr=subprocess.STDOUT)
        print(out)
    except subprocess.CalledProcessError as x:
        print(x.output)
        if "has no updates available" not in x.output:
            raise


def _resource_get(snapname):
    '''Used to fetch the resource path of the given name.

    This wrapper obtains a resource path and adds an additional
    check to return False if the resource is zero length.
    '''
    res_path = hookenv.resource_get(snapname)
    return res_path and os.stat(res_path).st_size != 0
