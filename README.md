# check_pakfire

``check_pakfire`` is a Nagios / Icinga plugin for checking [IPFire](http://www.ipfire.org) Pakfire updates and required reboots.

## Requirements

I successfully tested the plugin with **IPFire 2.x**. I'm not sure whether IPFire 3.x comes with a new Pakfire architecture - so, use this on newer versions at your own risk. ;-)

No additional Python packages are required - just deploy the script and use it.

**Note:** Beginning with plugin version **1.4**, Python 3 is the only supported version. If you're using an older IPFire release, you will need to use plugin version **1.3**.

## Usage

By default, the script checks for core updates and also packages upgrades - it is also possible to only check core updates (*``-e`` / ``--exclude-packages`` parameters*). Gathering performance data (*outdated packages*) can be useful when monitoring a big amount of IPFire systems.

The following parameters can be specified:

| Parameter | Description |
|:----------|:------------|
| `-d` / `--debug` | enable debugging outputs (*default: no*) |
| `-h` / `--help` | shows help and quits |
| `-e` / `--exclude-packages` | disables checking for package updates (*default: no*) |
| `-m` / `--mirror` | defines one or multiple mirrors (*default: system mirror list*) |
| `-n` / `--need-reboot` | defines exit level if reboot is required (*default: w*) |
| `-P` / `--show-perfdata` | enables performance data (*default: no*) |
| `-w` / `--packages-warning` | defines warning threshold for outdated packages (*default: 1*) |
| `-c` / `--packages-critical` | defines warning threshold for outdated packages (*default: 5*) |
| `-W` / `--core-warning` | defines warning threshold for outdated core (*default: 1*) |
| `-C` / `--core-critical` | defines warning threshold for outdated core (*default: 3*) |
| `--version` | prints programm version and quits |

### Examples

The following example checks for core updates only:

```shell
$ ./check_pakfire.py -e
OK: Core update (124) up2date
```

A IPFire host with some outdated packages:

```shell
$ ./check_pakfire.py
WARNING: Core update (124) up2date, packages outdated (linue-pae, lcd4linux)
```

An updated IPFire host with performance data:

```shell
$ ./check_pakfire.py
WARNING: Core update (124) up2date, packages outdated (linue-pae, lcd4linux) | 'system_updates'=0;;;; 'outdated_packages'=2.0;1.0;5.0;;
```

An outdated host with a pending reboot:

```shell
$ ./check_pakfire.py
CRITICAL: Core update (128) outdated (130), packages up2date, system reboot required
```

## Installation

To install the plugin, move the Python script into the appropriate directory and create a **configuration**.

## Configuration

### Nagios / Icinga 1.x

Within Nagios / Icinga you will need to configure a remote check command, e.g. for NRPE:

```text
# check_nrpe_pakfire
define command{
    command_name        check_nrpe_pakfire
    command_line        $USER1$/check_nrpe -H $HOSTADDRESS$ -c check_pakfire -a $ARG1$
}
```

Configure the check for a particular host, e.g.:

```text
# DIAG: Updates
define service{
        use                             generic-service
        host_name                       st-ipfire03
        service_description             DIAG: Updates
        check_command                   check_nrpe_pakfire!-P
}
```

### Icinga2

Define a service like this:

```text
apply Service "DIAG: Updates" {
  import "generic-service"
  check_command = "by_ssh"
  vars.by_ssh_command = [ "/opt/check_pakfire.py", "-P" ]
  vars.by_ssh_port = host.vars.ssh_port
  vars.by_ssh_logname = "icinga"
  assign where host.vars.os == "Linux" && host.vars.app == "router"
}
```

Define SSH port and application for your IPFire host:

```text
object Host "st-ipfire03.stankowic.loc" {
  import "generic-host"

  address = "xxx"

  vars.os = "Linux"
  vars.app = "router"

  vars.ssh_port = 222
}
```

Validate the configuration and reload the Icinga2 daemon:

```shell
# icinga2 daemon -C
# service icinga2 reload
```
