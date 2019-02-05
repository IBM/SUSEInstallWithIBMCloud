#!/usr/bin/python

import io
import sys
import argparse
from config import Config
from utils import get_ip

all_script_types = ['download', 'tftp']

#
# Prepare arg parse
#

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", metavar="CONF", required=True, help="the yaml configuration file")
parser.add_argument("--ip", dest="bootServerIP", metavar="IP", help="Bootserver IP to use. If not specified the current IP is used.")
parser.add_argument("--genDir", metavar="DIR", required=True, help="The output directory for the generated files")
parser.add_argument("--scripts", metavar="TYPE1[,TYPE2...]", required=True, help="The type of config to generate. Possible values: %s or 'all'" % ', '.join(all_script_types))

#
# Parse args
#
args = parser.parse_args()

#
# Check args
#
if args.scripts is not None:
    if ',' in args.scripts:
        scripts = args.scripts.split(',')
    elif args.scripts == 'all':
        scripts = all_script_types
    else:
        scripts = [args.scripts]
    
    for scriptType in scripts:
        if scriptType not in all_script_types:
            print("ERROR: invalid script type '%s' specified. Valid values are: %s" % (scriptType, ', '.join(all_script_types)))
            sys.exit(1)

#
# First check for the boot server IP.  If the option not specified,
# then get the current IP on first NIC of current OS
#
if 'bootServerIP' not in args or args.bootServerIP is None:
    args.bootServerIP = get_ip()

print( "Params:")
print("\tconfig: %s\n\tboot server IP: %s\n\tGEN DIR: %s\n\tScripts: %s\n\tcomputed scripts: %s" % (args.config,args.bootServerIP, args.genDir, args.scripts, scripts))

# Create the config instance which will be used to generate the SFTP and files.
cfg = Config(args.config,args.bootServerIP)

if 'download' in scripts:
    print( "Generating download scripts." )
    cfg.generateDownloadScripts(args.genDir)

if 'tftp' in scripts:
    print( "Generating TFTP config and scripts")
    cfg.generateConfigForTFTP(args.genDir)
