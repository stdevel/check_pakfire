# check_pakfire
``check_pakfire`` is a Nagios / Icinga plugin for checking [IPFire](http://www.ipfire.org) Pakfire updates

# Requirements
I successfully tested the plugin with **IPFire 2.x**. I'm not sure whether IPFire 3.x comes with a new Pakfire architecture - so, use this on newer versions at your own risk. ;-)

No additional Python packages are required - just deploy the script and use it.

# Usage
By default, the script checks for core updates - it is also possible to check for updates of installed Pakfire packages (*``-i`` / ``--include-packages`` parameters*).

The following parameters can be specified:

| Parameter | Description |
|:----------|:------------|
| `-d` / `--debug` | enable debugging outputs (*default: no*) |
| `-h` / `--help` | shows help and quits |
| `-i` / `--include-packages` | also checks for package updates (*default: only core updates are checked*) |
| `-m` / `--mirror` | defines one or multiple mirrors (*default: system mirror list*) |
| `--version` | prints programm version and quits |

## Examples
The following example checks for core updates:
```
$ ./check_pakfire.py 
OK: Core Update '102' for release '2.19' up2date!
```

A IPFire host with some outdated packages:
```
$ ./check_pakfire.py -i
WARNING: Core Update '102' for release '2.19' up2date, but 3 package(s) outdated!
```

# Installation
To install the plugin, move the Python script into the appropriate directory and create a **NRPE configuration**.

# Configuration
Inside Nagios / Icinga you will need to configure a remote check command, e.g. for NRPE:
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
        check_command                   check_nrpe_pakfire!-i
}
```
