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

import subprocess

from charmhelpers.core import hookenv
from charms import reactive


def install(snapname, **kw):
    '''Install a snap.

    Snap will be installed from the coresponding resource if available,
    otherwise from the Snap Store.

    Sets the snap.installed.{snapname} state.
    '''
    res_path = hookenv.resource_get(snapname)
    if res_path is False:
        _install_store(snapname, **kw)
    else:
        _install_local(res_path, **kw)
    reactive.set_state('snap.installed.{}'.format(snapname))


def refresh(snapname, **kw):
    '''Update a snap.

    Snap will be pulled from the coresponding resource if available
    and reinstalled if it has changed. Otherwise a 'snap refresh' is
    run updating the snap from the Snap Store.
    '''
    # Note that once you upload a resource, you can't remove it.
    # This means we don't need to cope with an operator switching
    # from a resource provided to a store provided snap, because there
    # is no way for them to do that.
    res_path = hookenv.resource_get(snapname)
    if res_path is False:
        _refresh_store(snapname, *kw)
    else:
        _install_local(res_path, **kw)


def remove(snapname):
    subprocess.check_call(['snap', 'remove', snapname],
                          universal_newlines=True)
    reactive.remove_state('snap.installed.{}'.format(snapname))


def _snap_args(channel='stable', devmode=False, jailmode=False,
               force_dangerous=False, revision=None):
    if channel != 'stable':
        yield '--channel={}'.format(channel)
    if devmode is True:
        yield '--devmode'
    if jailmode is True:
        yield '--jailmode'
    if force_dangerous is True:
        yield '--force-dangerous'
    if revision is not None:
        yield '--revision={}'.format(revision)


def _install_local(path, **kw):
    key = 'snap.local.{}'.format(path)
    if (reactive.helpers.data_changed(key, kw) or
            reactive.helpers.any_file_changed([path])):
        cmd = ['snap', 'install']
        cmd.extend(_snap_args(**kw))
        cmd.append('--force-dangerous')  # TODO: required for local snaps?
        cmd.append(path)
        hookenv.log('Installing {} from local resource'.format(path))
        subprocess.check_call(cmd, universal_newlines=True)


def _install_store(snapname, **kw):
    cmd = ['snap', 'install']
    cmd.extend(_snap_args(**kw))
    cmd.append(snapname)
    hookenv.log('Installing {} from store'.format(snapname))
    subprocess.check_call(cmd, universal_newlines=True)


def _refresh_store(snapname, **kw):
    cmd = ['snap', 'refresh']
    cmd.extend(_snap_args(**kw))
    cmd.append(snapname)
    hookenv.log('Refreshing {} from store'.format(snapname))
    subprocess.check_call(cmd, universal_newlines=True)
