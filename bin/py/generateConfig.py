#!/usr/bin/python

import io
import argparse
from config import Config
from utils import get_ip

#
# Prepare arg parse
#
parser = argparse.ArgumentParser()
parser.add_argument("--config", metavar="CONF", required=True, help="the yaml configuration file")
parser.add_argument("--genDir", metavar="DIR", required=True, help="The output directory for the generated files")
parser.add_argument("--scripts", metavar="TYPE1[,TYPE2...]", required=True, help="The type of config to generate. Possible values: download, tftp or all")

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
        scripts = ['download', 'tftp']
    else:
        scripts = [args.scripts]

myIP = get_ip()

print( "Params:")
print("\tconfig: %s\n\tboot server IP: %s\n\tGEN DIR: %s\n\tScripts: %s\n\tcomputed scripts: %s" % (args.config,myIP, args.genDir, args.scripts, scripts))

# Create the config instance which will be used to generate the SFTP and files.
cfg = Config(args.config,myIP)

if 'download' in scripts:
    print( "Generating download scripts." )
    cfg.generateDownloadScripts(args.genDir)

if 'tftp' in scripts:
    print( "Generating TFTP config and scripts")
    cfg.generateConfigForTFTP(args.genDir)
