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
sysRel=""
sysUpd=""
mirrList=[]
curUpd=""
curPkgs={}
sysPkgs={}



def getSystemVersion():
	#get system release and core update
	fRel = open('/etc/system-release', 'r')
	sRel = fRel.readline().strip()
	#define release and core version
	rel = re.search('2.[1-9]{1,2}', sRel)
	core = re.search('core[0-9]{1,3}', sRel)
	#return release and 'cleaned' core update
	if options.debug: print "RELEASE: {0}, UPDATE: {1}".format(rel.group(0), core.group(0).replace("core", ""))
	return [rel.group(0), core.group(0).replace("core", "")]
	
def getMirrorlist():
	#get system-wide mirror list
	fList = open('/opt/pakfire/db/lists/server-list.db', 'r')
	#finding all the mirrors
	list = []
	for line in fList.readlines():
		if "HTTP;" in line.rstrip():
			#add mirror
			list.append("http://{0}".format( line[line.find(";")+1:line.rfind(";")].replace(";", "/") ))
	if options.debug: print "MIRRORLIST: {0}".format(list)
	return list
	
def getRecentVersions():
	#get recent version(s) (core update and packages)
	for mirr in mirrList:
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
					cRel = re.search('[0-9]{1,3}', line)
					if options.debug: print "INFO: Recent core update is '{0}'".format(cRel.group(0))
			
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
			if cRel.group(0) != "" and len(pkgs) > 0: break
		except:
			if options.debug: print "ERROR: Unable to validate mirror '{0}'".format(mirr)
	#return value or die in a fire
	try:
		return cRel.group(0), pkgs
	except:
		print "UNKNOWN: No mirror could be reached for validating updates (hint: proxy or mirror list invalid?)"
		exit(3)

def getLocalPkgVersions():
	#get local installed package versions
	pkgs={}
	for root, dirs, files in os.walk("/opt/pakfire/db/installed", topdown=False):
		for name in files:
			#print(os.path.join(root, name))
			fPkg = open(os.path.join(root, name), 'r')
			for line in fPkg.readlines():
				if "Name" in line.rstrip(): myName = line.rstrip().replace("Name: ", "")
				if "ProgVersion" in line.rstrip(): myVers = line.rstrip().replace("ProgVersion: ", "")
				if "Release" in line.rstrip(): myRel = line.rstrip().replace("Release: ", "")
			#add if not core-upgrade (core updates are checked in a different way)
			if myName != "core-upgrade":
				if options.debug: print "LPKG: {0}, VERSION: {1}".format(myName, myVers+"."+myRel)
				pkgs.update({myName : myVers + "." + myRel })
	return pkgs

def checkUpdates():
	#check _all_ the updates!
	
	#check core update
	if float(curUpd) > float(sysUpd):
		#newer core update
		if options.debug: print "Installed core update '{0}' is older than most recent one '{1}'.".format(sysUpd, curUpd)
		boolCore = False
	else:
		#core up2date
		if options.debug: print "Installed core update '{0}' is up2date.".format(sysUpd)
		boolCore = True
	
	#check package updates
	if options.include_packages == True:
		outdated = [key for key, value in sysPkgs.items() if value != curPkgs.get(key)]
		if len(outdated) > 0: boolPkgs = False
		else: boolPkgs = True
	
	#exit with check result
	if options.include_packages == True:
		if boolCore == True and boolPkgs == True:
			#everything up2date
			print "OK: Core Update '{0}' and packages for release '{1}' up2date!".format(sysUpd, sysRel)
			exit(0)
		if boolCore == True and boolPkgs == False:
			print "WARNING: Core Update '{0}' for release '{1}' up2date, but {2} package(s) outdated!".format(sysUpd, sysRel, len(outdated))
			exit(1)
		if boolCore == False and boolPkgs == True:
			print "WARNING: Core Update '{0}' for release '{1}' outdated (current update: {2}), but packages up2date!".format(sysUpd, sysRel, curUpd)
			exit(1)
			
	else:
		#only check core update
		if boolCore == True:
			#core up2date
			print "OK: Core Update '{0}' for release '{1}' up2date!".format(sysUpd, sysRel)
			exit(0)
		else:
			#core outdated
			print "WARNING: Core Update '{0}' for release '{1}' outdated! (current update: {2})".format(sysUpd, sysRel, curUpd)
			exit(1)
	
	return False

if __name__ == "__main__":
	#define description, version and load parser
	desc='''%prog is used to check a IPFire host for pakfire updates (core updates and additional packages).
	
	Checkout the GitHub page for updates: https://github.com/stdevel/check_pakfire'''
	parser = OptionParser(description=desc,version="%prog version 1.0.0")
	
	genOpts = OptionGroup(parser, "Generic options")
	netOpts = OptionGroup(parser, "Network options")
	pkgOpts = OptionGroup(parser, "Package options")
	parser.add_option_group(genOpts)
	parser.add_option_group(netOpts)
	parser.add_option_group(pkgOpts)
	
	#-d / --debug
	genOpts.add_option("-d", "--debug", dest="debug", default=False, action="store_true", help="enable debugging outputs")
	
	#-i / --include-packages
	pkgOpts.add_option("-i", "--include-packages", dest="include_packages", default=False, action="store_true", help="also checks for package updates (default: only core updates are checked)")
	
	#-m / --mirror
	netOpts.add_option("-m", "--mirror", dest="mirrors", default=[], action="append", metavar="SERVER", help="defines one or multiple mirrors (default: system mirror list)")
	
	#parse arguments
	(options, args) = parser.parse_args()
	
	#debug outputs
	if options.debug: print "OPTIONS: {0}".format(options)
	
	#get system release, core update and package versions
	(sysRel, sysUpd) = getSystemVersion()
	sysPkgs = getLocalPkgVersions()
	
	#get mirror list
	if len(options.mirrors) >= 1: mirrList = options.mirrors
	else: mirrList = getMirrorlist()
	
	#get recent versions
	(curUpd, curPkgs) = getRecentVersions()
	
	#check for updates
	checkUpdates()
