# Snap layer

The Snap layer for Juju enables layered charms to more easily deal with
snap packages in a simple and efficient manner. It provides consistent
configuration for users, allowing them the choice of pulling snaps
from the main snap store, or uploading them as Juju resources for deploys
in environments with limited network access.

## Configuration

To have the Snap layer install snaps automatically, declare the snaps in
layer.yaml:

    ```yaml
    includes:
      - layer:basic
      - layer:snap
    options:
      snap:
        telegraf:
          channel: stable
          devmode: false
          jailmode: false
          force_dangerous: false
          revision: null
    ```

In addition, you should declare Juju resource slots for the snaps. This
allows operators to have snaps distributed from their Juju controller
node rather than the snap store, and is necessary for when your charm
is deployed in network restricted environments.

    ```yaml
    resources:
      telegraf:
        type: file
        filename: telegraf.snap
        description: Telegraf snap
    ```

With the Juju resource defined, the operator may deploy your charm
using locally provided snaps instead of the snap store:

    ```sh
    juju deploy --resource telegraf=telegraf_0_19.snap cs:telegraf
    ```

If your charm needs to control installation, update and removal of
snaps itself then do not declare the snaps in layer.yaml. Instead, use
the API provided by the `charms.layer.snap` Python package.
            

## Usage

If you have defined your snaps in layer.yaml for automatic installation
and updates, there is nothing further to do.


### API
  
If your charm need to control installation, update and removal of snaps
itself, the following methods are available via the `charms.layer.snap`
package::

* `install(snapname, **args)`. Install the snap from the corresponding Juju
  resource (using --force-dangerous implicitly). If the resource is not
  available, download and install from the Snap store using the provided
  keyword arguments.

* `refresh(snapname, **args)`. Update the snap. If the snap was installed
  from a local resource then the resource is checked for updates and the
  snap updated if the snap or arguments have changed. If the snap was
  installed from the Snap store, `snap refresh` is run to update the snap.

* `remove(snapname)`. The snap is removed.

Keyword arguments correspond to the layer.yaml options and snap command line
options. See the snap command line documentation for authorative details on
what these options do:

* `channel` (str)
* `devmode` (boolean)
* `jailmode` (boolean)
* `force_dangerous` (boolean)
* `revision` (str)


## Support

This layer is maintained on Launchpad by
Stuart Bishop (stuart.bishop@canonical.com).

Code is available using git at git+ssh://git.launchpad.net/layer-snap.

Bug reports can be made at https://bugs.launchpad.net/layer-snap.

Queries and comments can be made on the Juju mailing list, Juju IRC
channels, or at https://answers.launchpad.net/layer-snap.
