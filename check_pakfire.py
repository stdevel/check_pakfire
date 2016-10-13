#!/usr/bin/python

# check_pakfire.py - a script for checking a IPFire
# host for available pakfire updates
#
# 2016 By Christian Stankowic
# <info at stankowic hyphen development dot net>
# https://github.com/stdevel
#

from optparse import OptionParser, OptionGroup
import re
import urllib2
import os

#some script-wide variables
sys_rel=""
sys_upd=""
mirr_list=[]
cur_upd=""
cur_pkgs={}
sys_pkgs={}



def get_system_version():
	#get system release and core update
	f_rel = open('/etc/system-release', 'r')
	s_rel = f_rel.readline().strip()
	#define release and core version
	rel = re.search('2.[1-9]{1,2}', s_rel)
	core = re.search('core[0-9]{1,3}', s_rel)
	#return release and 'cleaned' core update
	if options.debug: print "RELEASE: {0}, UPDATE: {1}".format(rel.group(0), core.group(0).replace("core", ""))
	return [rel.group(0), core.group(0).replace("core", "")]
	
def get_mirrorlist():
	#get system-wide mirror list
	f_list = open('/opt/pakfire/db/lists/server-list.db', 'r')
	#finding all the mirrors
	list = []
	for line in f_list.readlines():
		if "HTTP;" in line.rstrip():
			#add mirror
			list.append("http://{0}".format( line[line.find(";")+1:line.rfind(";")].replace(";", "/") ))
	if options.debug: print "MIRRORLIST: {0}".format(list)
	return list
	
def get_recent_versions():
	#get recent version(s) (core update and packages)
	for mirr in mirr_list:
		#try a mirror
		try:
			#get core update version
			url = mirr+"/lists/core-list.db"
			if options.debug: print "INFO: Accessing URL '{0}'".format(url)
			req = urllib2.Request(url)
			res = urllib2.urlopen(req)
			file = res.read()
			file = file.split()
			for line in file:
				if "core_release" in line:
					c_rel = re.search('[0-9]{1,3}', line)
					if options.debug: print "INFO: Recent core update is '{0}'".format(c_rel.group(0))
			
			#get package versions
			pkgs={}
			url = mirr+"/lists/packages_list.db"
			if options.debug: print "INFO: Accessing URL '{0}'".format(url)
			req = urllib2.Request(url)
			res = urllib2.urlopen(req)
			file = res.read()
			file = file.split()
			for line in file:
				if ";" in line:
					#get package name and version, add to cache
					pkg = line[:line.find(';')]
					vers = line[line.find(';')+1:len(line)-1].replace(";", ".")
					if options.debug: print "PKG: {0}, VERSION: {1}".format(pkg, vers)
					pkgs.update({pkg : vers})
			#stahp if we got the information
			if c_rel.group(0) != "" and len(pkgs) > 0: break
		except:
			if options.debug: print "ERROR: Unable to validate mirror '{0}'".format(mirr)
	#return value or die in a fire
	try:
		return c_rel.group(0), pkgs
	except:
		print "UNKNOWN: No mirror could be reached for validating updates (hint: proxy or mirror list invalid?)"
		exit(3)

def get_local_pkg_versions():
	#get local installed package versions
	pkgs={}
	for root, dirs, files in os.walk("/opt/pakfire/db/installed", topdown=False):
		for name in files:
			f_pkg = open(os.path.join(root, name), 'r')
			for line in f_pkg.readlines():
				if "Name" in line.rstrip(): my_name = line.rstrip().replace("Name: ", "")
				if "ProgVersion" in line.rstrip(): my_vers = line.rstrip().replace("ProgVersion: ", "")
				if "Release" in line.rstrip(): my_rel = line.rstrip().replace("Release: ", "")
			#add if not core-upgrade (core updates are checked in a different way)
			if my_name != "core-upgrade":
				if options.debug: print "LPKG: {0}, VERSION: {1}".format(my_name, my_vers+"."+my_rel)
				pkgs.update({my_name : my_vers + "." + my_rel })
	return pkgs

def check_updates():
	#check _all_ the updates!
	perfdata=""
	
	#check core update
	if float(cur_upd) > float(sys_upd):
		#newer core update
		if options.debug: print "Installed core update '{0}' is older than most recent one '{1}'.".format(sys_upd, cur_upd)
		bool_core = False
	else:
		#core up2date
		if options.debug: print "Installed core update '{0}' is up2date.".format(sys_upd)
		bool_core = True
	
	#TODO: counter/diff warn/crit pkgs!
	
	#check package updates
	if options.exclude_pkgs == False:
		#get outdates packages
		outdated = [key for key, value in sys_pkgs.items() if value != cur_pkgs.get(key)]
		#TODO: wtf
		if len(outdated) > 0: bool_pkgs = False
		else: bool_pkgs = True
		#get performance data
		if options.show_perfdata: perfdata = " | 'outdated_packages'={0};{1};{2};;".format(float(len(outdated)), float(options.pkgs_warn), float(options.pkgs_crit))
	
	#exit with check result
	if options.exclude_pkgs == False:
		if bool_core == True and bool_pkgs == True:
			#everything up2date
			print "OK: Core Update '{0}' and packages for release '{1}' up2date!{2}".format(sys_upd, sys_rel, perfdata)
			exit(0)
		if bool_core == True and bool_pkgs == False:
			print "WARNING: Core Update '{0}' for release '{1}' up2date, but {2} package(s) outdated!{3}".format(sys_upd, sys_rel, len(outdated), perfdata)
			exit(1)
		if bool_core == False and bool_pkgs == True:
			print "WARNING: Core Update '{0}' for release '{1}' outdated (current update: {2}), but packages up2date{3}!".format(sys_upd, sys_rel, cur_upd, perfdata)
			exit(1)
			
	else:
		#only check core update
		if bool_core == True:
			#core up2date
			print "OK: Core Update '{0}' for release '{1}' up2date!{2}".format(sys_upd, sys_rel, perfdata)
			exit(0)
		else:
			#core outdated
			print "WARNING: Core Update '{0}' for release '{1}' outdated! (current update: {2}){3}".format(sys_upd, sys_rel, cur_upd, perfdata)
			exit(1)
	
	return False

if __name__ == "__main__":
	#define description, version and load parser
	desc='''%prog is used to check a IPFire host for pakfire updates (core updates and additional packages).
	
	Checkout the GitHub page for updates: https://github.com/stdevel/check_pakfire'''
	parser = OptionParser(description=desc,version="%prog version 1.0.5")
	
	gen_opts = OptionGroup(parser, "Generic options")
	net_opts = OptionGroup(parser, "Network options")
	pkg_opts = OptionGroup(parser, "Package options")
	parser.add_option_group(gen_opts)
	parser.add_option_group(net_opts)
	parser.add_option_group(pkg_opts)
	
	#-d / --debug
	gen_opts.add_option("-d", "--debug", dest="debug", default=False, action="store_true", help="enable debugging outputs")
	
	#-P / --show-perfdata
	gen_opts.add_option("-P", "--show-perfdata", dest="show_perfdata", default=False, action="store_true", help="enables performance data, requires -i (default: no)")
	
	#-e / --exclude-packages
	pkg_opts.add_option("-e", "--exclude-packages", dest="exclude_pkgs", default=False, action="store_true", help="disables checking for package updates (default: no)")
	
	#-w / --packages-warning
	pkg_opts.add_option("-w", "--packages-warning", dest="pkgs_warn", default=5, action="store", metavar="NUMBER", help="defines warning threshold for outdated packages (default: 5)")
	
	#-c / --packages-critical
	pkg_opts.add_option("-c", "--packages-critical", dest="pkgs_crit", default=10, action="store", metavar="NUMBER", help="defines critical threshold for outdated packages (default: 10)")
	
	#-m / --mirror
	net_opts.add_option("-m", "--mirror", dest="mirrors", default=[], action="append", metavar="SERVER", help="defines one or multiple mirrors (default: system mirror list)")
	
	#parse arguments
	(options, args) = parser.parse_args()
	
	#debug outputs
	if options.debug: print "OPTIONS: {0}".format(options)
	
	#get system release, core update and package versions
	(sys_rel, sys_upd) = get_system_version()
	sys_pkgs = get_local_pkg_versions()
	
	#get mirror list
	if len(options.mirrors) >= 1: mirr_list = options.mirrors
	else: mirr_list = get_mirrorlist()
	
	#get recent versions
	(cur_upd, cur_pkgs) = get_recent_versions()
	
	#check for updates
	check_updates()
