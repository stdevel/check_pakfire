#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A Nagios/Icinga plugin for checking a IPFire host
# for available Pakfire updates
"""

import argparse
import logging
import re
import os
from urllib import request
import sys

# some global variables
__version__ = "1.4.0"
LOGGER = logging.getLogger('check_pakfire')
"""
logging: Logger instance
"""
LOG_LEVEL = None
"""
logging: Logger level
"""
MIRROR_LIST = []
"""
str: Mirror list
"""
CORE_SYSTEM = 0
"""
str: Installed core update
"""
CORE_RECENT = 0
"""
str: Recent core update
"""
PACKAGES_SYSTEM = ""
"""
str: Installed package list
"""
PACKAGES_RECENT = ""
"""
str: Recent package list
"""
RETURN_CODE = 0
"""
int: Nagios/Icinga return code
"""


def get_system_version():
    """
    Gets system release and core update
    :return: system release, core update
    """

    try:
        release_file = open('/etc/system-release', 'r')
        release_str = release_file.readline().strip()
        # define release and core version
        release_system = re.search('2.[1-9]{1,2}', release_str)
        core_system = re.search('core[0-9]{1,3}', release_str)
        # return release and 'cleaned' core update
        LOGGER.debug(
            "System release: %s, System update: %s",
            release_system.group(0), core_system.group(0).replace("core", "")
        )
        return [release_system.group(0), core_system.group(0).replace("core", "")]
    except IOError:
        LOGGER.error("System release file not found (is this really a IPFire system?!)")
        sys.exit(3)


def get_mirror_list():
    """
    Retrieves the system-wide Pakfire mirror list

    :return: mirror list
    """
    mirror_list_file = open('/opt/pakfire/db/lists/server-list.db', 'r')
    # finding all the mirrors
    mirrors = []
    for line in mirror_list_file.readlines():
        if "HTTPS;" in line.rstrip():
            # add mirror
            mirrors.append(
                "https://{0}".format(line[line.find(";") + 1:line.rfind(";")].replace(";", "/"))
            )
    LOGGER.debug("Mirror list: %s", mirrors)
    return mirrors


def get_local_package_versions():
    """
    Retrieves a list of local installed package versions
    :return: package list
    """
    packages_local = {}
    package_name = ""
    package_version = ""
    package_release = ""
    for root, dirs, files in os.walk("/opt/pakfire/db/installed", topdown=False):
        for name in files:
            f_pkg = open(os.path.join(root, name), 'r')
            for line in f_pkg.readlines():
                if "Name" in line.rstrip():
                    package_name = line.rstrip().replace("Name: ", "")
                if "ProgVersion" in line.rstrip():
                    package_version = line.rstrip().replace("ProgVersion: ", "")
                if "Release" in line.rstrip():
                    package_release = line.rstrip().replace("Release: ", "")
            # add if not core-upgrade (core updates are checked in a different way)
            if package_name != "core-upgrade":
                LOGGER.debug(
                    "Local package: %s, version: %s", package_name,
                    package_version + "." + package_release
                )
                packages_local.update({package_name: package_version + "." + package_release})
    return packages_local


def get_recent_versions():
    """
    Retrieves recent IPFire Core Update and package versions
    :return: version list
    """
    packages_recent = {}
    core_recent = None
    for mirror in MIRROR_LIST:
        # try a mirror
        LOGGER.debug("Trying mirror '%s'", mirror)
        try:
            # get core update version
            url = mirror + "/lists/core-list.db"
            LOGGER.debug("Accessing URL '%s'", url)
            result = request.urlopen(url)
            core_list = result.read().decode('utf-8')
            core_list = core_list.split()
            for line in core_list:
                if "core_release" in line:
                    core_recent = re.search('[0-9]{1,3}', line)
                    LOGGER.debug(
                        "Recent core update is '%s'", core_recent.group(0)
                    )

            # get package versions
            url = mirror + "/lists/packages_list.db"
            LOGGER.debug("Accessing URL '%s'", url)
            result = request.urlopen(url)
            packages_list = result.read().decode('utf-8')
            packages_list = packages_list.split()
            for line in packages_list:
                if ";" in line:
                    # get package name and version, add to cache
                    this_package = line[:line.find(';')]
                    this_version = line[line.find(';') + 1:len(line) - 1].replace(";", ".")
                    LOGGER.debug(
                        "Recent package: %s, version: {%s}", this_package, this_version
                    )
                    packages_recent.update({this_package: this_version})
            # stop if we got the information
            if core_recent.group(0) != "" and packages_recent:
                break
        except IOError as err:
            LOGGER.error(
                "Unable to validate mirror '%s': '%s'", mirror, str(err)
            )
    # return value or die in a fire
    try:
        return core_recent.group(0), packages_recent
    except AttributeError:
        print("UNKNOWN: No mirror could be reached for validating " \
              "updates (hint: proxy or mirror list invalid?)")
        sys.exit(3)


def check_updates():
    """
    Checks Core and package updates and for required reboot and returns Nagios/Icinga result data
    """
    # check _all_ the updates!
    perfdata = ""
    packages_outdated = {}
    LOGGER.debug("Checking updates")

    # check core update
    core_difference = int(CORE_RECENT) - int(CORE_SYSTEM)
    if core_difference >= OPTIONS.core_critical:
        status_message = "Core update ({0}) outdated ({1})".format(CORE_SYSTEM, CORE_RECENT)
        set_return_code(2)
    elif core_difference >= OPTIONS.core_warning:
        status_message = "Core update ({0}) outdated ({1})".format(CORE_SYSTEM, CORE_RECENT)
        set_return_code(1)
    else:
        status_message = "Core update ({0}) up2date".format(CORE_SYSTEM)

    # check package updates
    if not OPTIONS.packages_exclude:
        packages_outdated = [key for key, value in PACKAGES_SYSTEM.items() if value != PACKAGES_RECENT.get(key)]
        packages_outdated_list = "{0}".format(", ".join(packages_outdated))
        LOGGER.debug("Outdated packages: (%s)", packages_outdated_list)

        # compare thresholds
        if len(packages_outdated) >= OPTIONS.packages_critical:
            # critical threshold exceeded
            status_message = "{0}, packages outdated ({1})".format(
                status_message, packages_outdated_list
            )
            set_return_code(2)
        elif len(packages_outdated) >= OPTIONS.packages_warning:
            # warning threshold exceeded
            status_message = "{0}, packages outdated ({1})".format(
                status_message, packages_outdated_list
            )
            set_return_code(1)
        elif not packages_outdated:
            # packages up2date
            status_message = "{0}, packages up2date".format(status_message)
        else:
            # some packages outdated but we don't care
            status_message = "{0}, packages outdated ({1})".format(
                status_message, packages_outdated_list
            )

    # get performance data
    if OPTIONS.show_perfdata:
        # core update
        perfdata = " | 'system_updates'={0};{1};{2};;".format(
            int(int(CORE_RECENT) - int(CORE_SYSTEM)),
            int(OPTIONS.core_warning), int(OPTIONS.core_critical)
        )
        # package updates
        if not OPTIONS.packages_exclude:
            perfdata = "{0} 'outdated_packages'={1};{2};{3};;".format(
                perfdata, int(len(packages_outdated)),
                int(OPTIONS.packages_warning), int(OPTIONS.packages_critical)
            )

    # check if reboot is required
    if os.path.isfile('/var/run/need_reboot'):
        if OPTIONS.need_reboot == 'c':
            status_message = "{0}, system reboot required".format(
                status_message
            )
            set_return_code(2)
        elif OPTIONS.need_reboot == 'w':
            status_message = "{0}, system reboot required".format(
                status_message
            )
            set_return_code(1)

    # print output and die in a fire
    print(
        "{0}: {1} {2}".format(get_return_string(), status_message, perfdata)
    )
    sys.exit(RETURN_CODE)


def set_return_code(code):
    """
    This functions sets the return to a new value if it is higher
    Refer to the following possible codes:
    0: OK
    1: WARNING
    2: CRITICAL
    3: UNKNOWN

    :param code: Nagios/Icinga return code
    :type code: int
    """
    global RETURN_CODE
    # change return code if higher
    if code > RETURN_CODE:
        RETURN_CODE = code


def get_return_string():
    """
    This function returns the result status based on the state code.

    :return: str
    """
    if RETURN_CODE == 3:
        return_string = "UNKNOWN"
    elif RETURN_CODE == 2:
        return_string = "CRITICAL"
    elif RETURN_CODE == 1:
        return_string = "WARNING"
    else:
        return_string = "OK"
    return return_string


def parse_options():
    """
    Parses options and arguments.
    :return: parser options
    """
    # define description, version and load parser
    desc = '''%prog is used to check a IPFire host for Pakfire updates
 (core updates and additional packages).'''
    epilog = '''Check-out the website for more details:
    http://github.com/stdevel/check_pakfire'''
    parser = argparse.ArgumentParser(description=desc, epilog=epilog)
    parser.add_argument('--version', action='version', version=__version__)

    gen_opts = parser.add_argument_group("Generic options")
    net_opts = parser.add_argument_group("Network options")
    pkg_opts = parser.add_argument_group("Package options")

    # -d / --debug
    gen_opts.add_argument("-d", "--debug", dest="generic_debug", default=False,
                          action="store_true", help="enable debugging outputs")

    # -P / --show-perfdata
    gen_opts.add_argument("-P", "--show-perfdata", dest="show_perfdata",
                          default=False, action="store_true",
                          help="enables performance data (default: no)")

    # -e / --exclude-packages
    pkg_opts.add_argument("-e", "--exclude-packages", dest="packages_exclude",
                          default=False, action="store_true",
                          help="disables checking for package updates (default: no)")

    # -w / --packages-warning
    pkg_opts.add_argument("-w", "--packages-warning", dest="packages_warning", default=1,
                          action="store", type=int, metavar="INTEGER",
                          help="defines warning threshold for outdated packages (default: 1)")

    # -c / --packages-critical
    pkg_opts.add_argument("-c", "--packages-critical", dest="packages_critical", default=5,
                          action="store", type=int, metavar="INTEGER",
                          help="defines critical threshold for outdated packages (default: 5)")

    # -W / --core-warning
    pkg_opts.add_argument("-W", "--core-warning", dest="core_warning", default=1, action="store",
                          metavar="INTEGER", type=int,
                          help="defines warning threshold for outdated core (default: 1)")

    # -C / --core-critical
    pkg_opts.add_argument("-C", "--core-critical", dest="core_critical", default=3, action="store",
                          metavar="INTEGER", type=int,
                          help="defines critical threshold for outdated core (default: 3)")

    # -m / --mirror
    net_opts.add_argument("-m", "--mirror", dest="mirrors", default=[], action="append",
                          metavar="SERVER",
                          help="defines one or multiple mirrors (default: system mirror list)")

    # -n / --need-reboot
    pkg_opts.add_argument("-n", "--need-reboot", dest="need_reboot", default="w",
                          action="store", type=str.lower, metavar="w|c",
                          help="defines exit level if reboot is required (default: w)")

    # parse arguments
    parser_options = parser.parse_args()
    return parser_options


if __name__ == "__main__":
    # set log level
    OPTIONS = parse_options()

    # set logging level
    logging.basicConfig()
    if OPTIONS.generic_debug:
        LOG_LEVEL = logging.DEBUG
    else:
        LOG_LEVEL = logging.ERROR
    LOGGER.setLevel(LOG_LEVEL)
    LOGGER.debug("Options: %s", OPTIONS)

    # get system release, core update and package versions
    (SYSTEM_RELEASE, CORE_SYSTEM) = get_system_version()
    PACKAGES_SYSTEM = get_local_package_versions()

    # get mirror list from options or system
    if len(OPTIONS.mirrors) >= 1:
        MIRROR_LIST = OPTIONS.mirrors
    else:
        MIRROR_LIST = get_mirror_list()

    # get recent versions
    (CORE_RECENT, PACKAGES_RECENT) = get_recent_versions()

    # check for updates
    check_updates()
