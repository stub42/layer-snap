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
from charmhelpers.core import hookenv
from charms import layer
from charms import reactive
from charms.layer import snap
from charms.reactive import hook


def install():
    opts = layer.options('snap')
    for snapname, snap_opts in opts.items():
        state = 'snap.installed.{}'.format(snapname)
        if not reactive.is_state(state):
            snap.install(snapname, **snap_opts)


def refresh():
    opts = layer.options('snap')
    for snapname, snap_opts in opts.items():
        snap.refresh(snapname, **snap_opts)


@hook('upgrade-charm')
def upgrade_charm():
    refresh()


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
    hookenv.atstart(install)
    reactive._snap_registered = True
