# check_pakfire
``check_pakfire`` is a Nagios / Icinga plugin for checking [IPFire](http://www.ipfire.org) Pakfire updates.

# Requirements
I successfully tested the plugin with **IPFire 2.x**. I'm not sure whether IPFire 3.x comes with a new Pakfire architecture - so, use this on newer versions at your own risk. ;-)

No additional Python packages are required - just deploy the script and use it.

# Usage
By default, the script checks for core updates and also packages upgrades - it is also possible to only check core updates (*``-e`` / ``--exclude-packages`` parameters*). Gathering performance data (*outdated packages*) can be useful when monitoring a big amount of IPFire systems.

The following parameters can be specified:

| Parameter | Description |
|:----------|:------------|
| `-d` / `--debug` | enable debugging outputs (*default: no*) |
| `-h` / `--help` | shows help and quits |
| `-l` / `--list-packages` | lists outdated packages (*default: no*) |
| `-e` / `--exclude-packages` | disables checking for package updates (*default: no*) |
| `-m` / `--mirror` | defines one or multiple mirrors (*default: system mirror list*) |
| `-P` / `--show-perfdata` | enables performance data (*default: no*) |
| `-w` / `--packages-warning` | defines warning threshold for outdated packages (*default: 5*) |
| `-c` / `--packages-critical` | defines warning threshold for outdated packages (*default: 10*) |
| `--version` | prints programm version and quits |

## Examples
The following example checks for core updates only:
```
$ ./check_pakfire.py  -e
OK: Core Update '105' for release '2.19' up2date!
```

A IPFire host with some outdated packages:
```
$ ./check_pakfire.py
WARNING: Core Update '105' for release '2.19' up2date, but 3 package(s) outdated!
```

The same example with listing the outdated packages:
```
$ ./check_pakfire.py -l
WARNING: Core Update '105' for release '2.19' up2date, but 3 package(s) (hostapd, nagios, libgiertz) outdated!
```

An updated IPFire host with performance data:
```
$ ./check_pakfire.py
OK: Core Update '105' and packages for release '2.19' up2date! | 'outdated_packages'=0.0;5.0;10.0;;
```

# Installation
To install the plugin, move the Python script into the appropriate directory and create a **configuration**.

# Configuration

## Nagios / Icinga 1.x
Within Nagios / Icinga you will need to configure a remote check command, e.g. for NRPE:
```
#check_nrpe_pakfire
define command{
    command_name        check_nrpe_pakfire
    command_line        $USER1$/check_nrpe -H $HOSTADDRESS$ -c check_pakfire -a $ARG1$
}
```

Configure the check for a particular host, e.g.:
```
#DIAG: Updates
define service{
        use                             generic-service
        host_name                       st-ipfire02
        service_description             DIAG: Updates
        check_command                   check_nrpe_pakfire!-P
}
```

## Icinga2
Define a service like this:
```
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
```
object Host "st-ipfire02.stankowic.loc" {
  import "generic-host"

  address = "xxx"

  vars.os = "Linux"
  vars.app = "router"

  vars.ssh_port = 222
}
```

Validate the configuration and reload the Icinga2 daemon:
```
# icinga2 daemon -C
# service icinga2 reload
```
