#!/usr/bin/python
import os
import sys
import crypt
import argparse
import SoftLayer
from BaseHTTPServer import HTTPServer

from utils import get_ip, ipToHex, restartDHCP, restartDevice
from softlayer_helper import SoftLayerHelper, Device, DeviceType, SubnetType, SubnetAddressSpace, Subnet, VLAN
from dhcp_conf_helper import DhcpConfEntry, DhcpConfEntryType, DhcpConfHelper
from templates import Templates
from config import Config
from notif_handler import NotificationHandler


PROG_ENV_VAR='PROG_NAME'

#
# Function: create_parser
#
def create_parser(progName=os.environ[PROG_ENV_VAR] if PROG_ENV_VAR in os.environ else None):
    # create the top-level parser
    parser = argparse.ArgumentParser(progName if progName else None)
    parser.add_argument("-c", "--config", metavar="YAML_CONF", required=True, help="the yaml configuration file")
    parser.add_argument("--sl-user", metavar="USER", help="SoftLayer username (or environment variables SL_USER and SL_USERNAME)")
    parser.add_argument("--sl-apikey", metavar="KEY", help="SoftLayer API key (or environment variable SL_APIKEY and SL_API_KEY)")
    parser.add_argument("--ip", dest="bootServerIP", metavar="IP", help="Bootserver IP to use. If not specified the current IP is used.")

    subparsers = parser.add_subparsers(title='Sub commands')

    # create the parser for the "prepare" command
    parser_prepare = subparsers.add_parser('prepare', help='Update the DHCP and autoyast config for hosts to install OS')
    group_prepare = parser_prepare.add_mutually_exclusive_group(required=True)
    group_prepare.add_argument("--hostname", metavar="HOST[,HOST...]", help="hostname(s) for which to create DHCP config")
    group_prepare.add_argument("--tag", metavar="TAG[,TAG...]", help="tag(s) for which to find the hosts to create DHCP")
    parser_prepare.add_argument("--unencryptedPassword", action="store_true", default=False, help="Leave root password unencrypted in the generated autoyast file. Default is to encrypt the password")
    parser_prepare.set_defaults(func=prepareHosts)

    # create the parser for the "delete" command
    parser_delete = subparsers.add_parser('delete', help='Remove the DHCP and config for currently configured hosts')
    # group_delete = parser_delete.add_argument_group('Specify one of the following')
    group_delete = parser_delete.add_mutually_exclusive_group(required=True)
    group_delete.add_argument("--hostname", metavar="HOST[,HOST...]", help="hostname(s) for which to remove DHCP config")
    group_delete.add_argument("--tag", metavar="TAG[,TAG...]", help="tag(s) for which to find the hosts to remove DHCP")
    parser_delete.set_defaults(func=deleteHosts)

    # create the parser for the "apply" command
    parser_apply = subparsers.add_parser('apply', help='Apply the current DHCP and autoyast config and initiate install OS')
    # group_apply = parser_apply.add_argument_group('Optional parameters')
    group_apply = parser_apply.add_mutually_exclusive_group(required=False)
    group_apply.add_argument("--show", action="store_true", help="Show the current hosts configured for installation")
    group_apply.add_argument("--listenOnly", action="store_true", help="Only start the listener (in case there was a failure)")
    parser_apply.set_defaults(func=installHosts)

    return parser

#
# Function: preProcessArgs
#
def preProcessArgs(args):
    #
    # First check for the boot server IP.  If the option not specified,
    # then get the current IP on first NIC of current OS
    #
    if 'bootServerIP' not in args or args.bootServerIP is None:
        args.bootServerIP = get_ip()

    #
    # Create the config instance which will be used to generate the SFTP and files.
    #
    args.bootServerListenPort = 8888
    args.cfg = Config(args.config,args.bootServerIP)
    args.valid_tags = args.cfg.getMachineTags()

    #
    # Setup tags param (if --tag used)
    #
    if 'tag' in args and args.tag: #args.tag:
        if ',' in args.tag:
            args.tags = args.tag.split(',')

        elif args.tag == 'all':
            args.tags = args.valid_tags
        else:
            args.tags = [args.tag]
        # Once tags are set, verify they are valid tags.
        for tag in args.tags:
            if tag not in args.valid_tags:
                print("\nERROR: invalid tag specified.  Valid values are: %s\n" % ', '.join(args.valid_tags))
                sys.exit(1)
    #
    # Setup hostnames param (if --hostname used)
    #
    if 'hostname' in args and args.hostname: #args.hostname:
        if ',' in args.hostname:
            args.hostnames = args.hostname.split(',')
        else:
            args.hostnames = [args.hostname]

    #
    # First retrieve the mentioned devices and also any existing host entries in the dhcp config
    #
    args.slHelper = SoftLayerHelper()
    args.vlan = args.slHelper.getVlan(args.cfg.vlanIdOrName, subnetType=SubnetType.Portable, addressSpace=SubnetAddressSpace.Private)

    if not args.vlan:
        print("\nERROR: Cannot find matching VLAN based on the configuration.")
        sys.exit(1)

    #
    # Setup the DHCP conf helper and related variables
    #
    args.dhcpConf = DhcpConfHelper('/etc/dhcp/dhcpd.conf')
    args.dhcpSharedNet = args.dhcpConf.getRootEntry().getFirstChild(DhcpConfEntryType.Shared_Network)
    args.dhcpGroup = args.dhcpConf.getRootEntry().findChild(DhcpConfEntryType.Group)

    if args.dhcpSharedNet is None or args.dhcpGroup is None:
        print("\nERROR: The dhcpd.conf file does have the structure expected. Run the configuration on the bootserver again.")
        sys.exit(1)

    args.hosts = args.dhcpGroup.getChildren(DhcpConfEntryType.Host)
    return args

#
# Function: runListener
#
def runListener(bootServerListenPort, dhcpConf, dhcpGroup):
    """
    Launches a HTTP listener to wait for updates from the servers being installed.
    When all have been processed, then it quits.
    """
    server = None

    try:
        # Create the server and define the handler to manage the incomming requests
        server = HTTPServer(('', bootServerListenPort), NotificationHandler)
        print("Started listener on port %s and waiting for servers' responses." % bootServerListenPort)
        
        NotificationHandler.setDhcpConfFilename(dhcpConf.getFilename())
        NotificationHandler.setServer(server)

        # Wait forever for incoming http requests
        server.serve_forever()

    except KeyboardInterrupt:
        print '^C received, shutting down the listener'
        server.socket.close()

#
# Function: getDeviceInstallTag
#
def getDeviceInstallTag(valid_tags, device):
    """
    It goes through the tags on the device and the "valid" tags in the config.
    The device should match only one of the valid tags
    """
    matchedTags = 0
    matchedTag = None

    for tag in valid_tags:
        if tag in device.tags:
            matchedTags += 1
            matchedTag = tag
    
    if matchedTags > 1:
        raise Exception("Only one of these tags should be in device.  Device tags: %s.  Valid tags: %s" % (device.tags, valid_tags))

    return matchedTag

#
# Function: getMachineConfForDevice
#
def getMachineConfForDevice(cfg, device):
    deviceTag = getDeviceInstallTag(cfg.getMachineTags(),device)
    machineConf = cfg.getMachine(deviceTag)

    if not deviceTag:
        print("\nERROR: No match in the config file for device with id '%s' and tags: %s" % (device.id, ', '.join(device.tags)))
        sys.exit(1)
    elif not machineConf:
        print("\nERROR: Unable to find machine configuration for tag: %s.  Device id=%s and device tags=%s" % (deviceTag, device.id, ', '.join(device.tags)))
        sys.exit(1)
    return machineConf

#
# Function: generateAutoyastFile
#
def generateAutoyastFile(cfg, bootServerIP, bootServerPort, ip, subnet, device, machineConf, unencryptedPassword=True):
    """
    Generate the autoyast file for target server.
    """
    vars = {
        'target_ip': ip,
        'target_hostname': device.hostname,
        'target_domain': device.domain,
        'target_root_password': device.password if unencryptedPassword else crypt.crypt(device.password),
        'target_password_encrypted': 'false' if unencryptedPassword else 'true',
        'subnet_netmask': subnet.netmask,
        'subnet_net_prefix': subnet.cidr,
        'subnet_gateway': subnet.gateway,
        'bootserver_ip': bootServerIP,
        'bootserver_listen_port': bootServerPort
    }
    outFile = cfg.generateAutoyastFile(machineConf['yast_template'], ipToHex(ip), vars)
    print("Autoyast file generated for host '%s': %s" % (device.hostname,outFile))

#
# Function: generateSubnetEntry
#
def generateSubnetEntry(cfg, bootServerIP, subnet):
    """
    Generate a subnet entry instance for the provided subnet.
    """
    vars = {
        'bootServerIP': bootServerIP,
        'subnet_ip': subnet.network,
        'subnet_netmask': subnet.netmask,
        'subnet_broadcast': subnet.broadcast,
        'subnet_gateway': subnet.gateway
    }
    subnetText = cfg.generateDhcpSubnetEntryText(vars)
    return DhcpConfHelper().readText(subnetText).getRootEntry().getFirstChild(DhcpConfEntryType.Subnet)

#
# Function: addDhcpSubnetEntry
#
def addDhcpSubnetEntry(cfg, bootServerIP, subnet, dhcpSharedNet):
    """
    Adds a subnet entry in the shared-network section if not already there.
    Return True or False, depending on whether the entry was added or not.
    """
    # First we check if the subnet entry need to be created.
    subnetStr = "%s/%s" % (subnet.network, subnet.cidr)

    # If it is already there, nothing to do.
    if dhcpSharedNet.contains(DhcpConfEntryType.Subnet, subnet.network):
        print("Subnet %s already configured in DHCP configuration." % subnetStr)
        return False

    # Otherwise, we need to add the new subnet entry
    dhcpSharedNet.addChild(generateSubnetEntry(cfg, bootServerIP, subnet))
    print("Added subnet %s configuration to DHCP" % subnetStr)
    return True

#
# Function: generateHostEntry
#
def generateHostEntry(cfg, ip, device, machineConf):
    """
    Generate a host entry instance for the provided device.
    """
    vars = {
        'server_hostname': device.hostname,
        'server_mac_address': device.mac,
        'server_ip': ip,
        'server_image': machineConf['image']
    }

    hostText = cfg.generateDhcpHostEntryText(vars)
    return DhcpConfHelper().readText(hostText).getRootEntry().getFirstChild(DhcpConfEntryType.Host)

#
# Function: addDhcpHostEntry
#
def addDhcpHostEntry(dhcpGroup, hostEntry):
    """
    Adds a host entry in the group section if not already there.
    Return True or False, depending on whether the entry was added or not.
    """

    # Next we check if the host entry needs to be created.
    if dhcpGroup.contains(DhcpConfEntryType.Host, hostEntry.name):
        print("Entry for hostname '%s' already exists in DHCP cofiguration." % hostEntry.name)
        return False
    
    dhcpGroup.addChild(hostEntry)
    print("Added the DHCP host configuration entry for %s" % hostEntry.name)
    return True

#
# Function: removeDhcpHostEntry
#
def removeDhcpHostEntry(dhcpGroup, hostname):
    """
    Removes the entry from the group section if present.
    Returns True or False, depending on whether the entry wass removed or not
    """
    if dhcpGroup.removeChild(DhcpConfEntryType.Host, hostname):
        print("DHCP configuration for host '%s' removed." % hostname)
        return True
    
    print("DHCP configuration for host '%s' not found." % hostname)
    return False

#
# Function: validateDeviceTags
#
def validateDeviceTags(valid_tags, devices):
    """
    Validate that all devices has the correct setup in the tags.
    Each device should only match one of the valid tags (those defined in the config)
    """
    if devices and len(devices) > 0:
        for device in devices:
            tagCount = 0
            for tag in valid_tags:
                if tag in device.tags:
                    tagCount += 1
            if tagCount > 1:
                print("\nERROR: Device with id '%s' (hostname %s) has multiple tags: %s. Only one of these tags must be assigned to the device: %s" % (device.id, device.hostname, ', '.join(device.tags), ', '.join(valid_tags)) )
                sys.exit(1)

#
# Function: gatherDeviceInfo
#
def gatherDeviceInfo(cfg, slHelper, hostnames=None, tags=None):
    """
    Collect the device information based on either a list of hostnames or a list of tags.
    The collected data is returned in a dictionary with the hostname as the key and the
    device as the value.
    """
    if (hostnames and tags) or (hostnames == None and tags == None):
        raise Exception("Only one of hostnames or tags must be specified.")

    valid_tags = cfg.getMachineTags()
    devices = []
    
    if hostnames:
        # Get all bare metal devices with the speficied hostnames.
        # However, a bare metal should not have multiple matching tags
        devices = slHelper.getDevicesByHostname(hostnames, DeviceType.BareMetal)
        # Make sure that we can retrieve device information for all hostnames specified.
        if devices == None or len(hostnames) != len(devices):
            missingHostnames = hostnames[:]
            if devices:
                for device in devices:
                    missingHostnames.remove(device.hostname)
            print("ERROR: Did not find matching devices for these hostnames specified: %s\n" % ', '.join(missingHostnames))
            sys.exit(1)
        validateDeviceTags(valid_tags, devices)
    else: # i.e. tags
        # Get all bare metal devices that have the requested tags.
        # However, a bare metal should not more than one of our configured tags
        devices = slHelper.getDevicesByTag(tags, deviceType=DeviceType.BareMetal)
        validateDeviceTags(valid_tags, devices)
    
    if devices and len(devices) > 0:
        deviceInfo = { }
        for device in devices:
            deviceInfo[device.hostname] = device
        return deviceInfo
    return None

#
# Function: prepareHosts
#
def prepareHosts(args):
    """
    Function called by the argument parser to process the "prepare" option
    """
    print("")

    deviceInfo = gatherDeviceInfo(args.cfg, args.slHelper, hostnames=args.hostnames if 'hostnames' in args else None, tags=args.tags if 'tags' in args else None)

    if deviceInfo and len(deviceInfo) > 0:
        hostnames = [hostname for hostname in deviceInfo]
        print("Going to configure DHCP for the following hosts: %s\n" % ', '.join(hostnames))

        changesMade = 0
        # First get the subnet for the boot server and make sure it is in the DHCP config
        mySubnet = args.slHelper.getSubnetForIP(args.bootServerIP)

        if mySubnet is None:
            print("ERROR: Cannot identify the subnet for the boot server at IP %s" % args.bootServerIP)
            return 1
        else:
            # Add the boot server's subnet if not already in the DHCP config
            if addDhcpSubnetEntry(args.cfg, args.bootServerIP, mySubnet, args.dhcpSharedNet):
                changesMade += 1
                print("")

        # Now for each host we check if an DHCP entries need to be created.
        for hostname in hostnames:
            device = deviceInfo[hostname]
            # We get the info on the reserved ip and its subnet
            ip,subnet = args.slHelper.findIpInfoByNoteInVlan(args.vlan, hostname)
            # Get the machine conf (image to use, etc)
            machineConf = getMachineConfForDevice(args.cfg, device)

            if ip and subnet:
                print("Hostname '%s': Reserved IP is %s and subnet %s/%s" % (hostname, ip, subnet.network, subnet.cidr))
                # Add the host's subnet if not already in the DHCP config
                if addDhcpSubnetEntry(args.cfg, args.bootServerIP, subnet, args.dhcpSharedNet):
                    changesMade += 1

                # Next we check if the host entry needs to be created.
                if addDhcpHostEntry(args.dhcpGroup, generateHostEntry(args.cfg, ip, device, machineConf)):
                    changesMade += 1
                print("")
            # Always generate the autoyast file since it may have changed
            generateAutoyastFile(args.cfg, args.bootServerIP, args.bootServerListenPort, ip, subnet, device, machineConf, args.unencryptedPassword)

        if changesMade > 0:
            if args.dhcpConf.save():
                print("\nChanges saved in %s\n" % args.dhcpConf.getFilename())
    return 0

#
# Function: deleteHosts
#
def deleteHosts(args):
    """
    Function called by the argument parser to process the "delete" option
    """
    print("")

    deviceInfo = gatherDeviceInfo(args.cfg, args.slHelper, hostnames=args.hostnames if 'hostnames' in args else None, tags=args.tags if 'tags' in args else None)

    if deviceInfo and len(deviceInfo) > 0:
        changesMade = 0
        # for hostname,device in deviceInfo.items():
        for hostname in deviceInfo:
            if removeDhcpHostEntry(args.dhcpGroup, hostname):
                changesMade += 1
        if changesMade > 0:
            if args.dhcpConf.save():
                print("\nChanges saved in %s\n" % args.dhcpConf.getFilename())
    else: # No host names
        print("ERROR: No matching hosts found")
        return 1
    return 0

#
# Function: installHosts
#
def installHosts(args):
    """
    Function called by the argument parser to process the "apply" option
    """
    print("")
    # Need to verify that all devices listed in the dhcpd.conf exist on SL.
    if args.hosts and len(args.hosts) > 0:
        if 'show' in args and args.show:
            print("The following hosts are setup in the DHCP configuration for OS installation:")
            for host in args.hosts:
                print("\tHost: %s" % host.name)
            return 0
        else:
            deviceInfo = { }
            for host in args.hosts:
                print( "Gathering information for: %s" % host.name)
                device = args.slHelper.getDeviceByHostname(host.name)
                if device:
                    deviceInfo[host.name] = device
                else:
                    print("ERROR: Was not able to find device info for hostname '%s" % host.name)
                    return 1
            if 'listenOnly' not in args or args.listenOnly == False:
                print("")
                # Restart DHCP
                if restartDHCP() != 0:
                        print("ERROR: Was not able to DHCP daemon service")
                        return 1
                for hostname,device in deviceInfo.items():
                    print( "Triggering OS install on host '%s' (SoftLayer device with id: %s)" % (hostname, device.id))
                    restartDevice(device.id)
            print("")
            runListener(args.bootServerListenPort, args.dhcpConf, args.dhcpGroup)
            return 0
    else:
        print("ERROR: No hosts configured in DHCP configution.")
        return 1


#############################################################################################
# Main logic here
#############################################################################################

#
# Parse args
#
print("")
parser = create_parser()
args = parser.parse_args()
rc = args.func(preProcessArgs(args))
#print("\nRC=%s\n" % rc)
print("")
sys.exit(rc)

