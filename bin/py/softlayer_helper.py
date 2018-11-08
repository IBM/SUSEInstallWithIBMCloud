import os
import SoftLayer
import json
import numbers
from utils import aton, ntoa, BaseEnum

class SubnetAddressSpace(BaseEnum):
    Public = "PUBLIC"
    Private = "PRIVATE"
    Any = "Any"

class SubnetType(BaseEnum):
    Primary = "ADDITIONAL_PRIMARY"
    Portable = "SECONDARY_ON_VLAN"
    Primary_IPV6 = "PRIMARY_6"
    Any = "Any"

class Subnet():
    """Entity that represent a softlayer subnet"""
    MASK = "id,networkIdentifier,netmask,broadcastAddress,gateway,addressSpace,subnetType"
    @staticmethod
    def getPrefix(netmask):
        "Get the subnet prefix given the netmask"
        prefix = sum([bin(int(x)).count('1') for x in netmask.split('.')])
        return prefix

    def __init__(self, subnet):
        self.id = subnet['id']
        self.network = subnet['networkIdentifier']
        self.netmask = subnet['netmask']
        self.broadcast = subnet['broadcastAddress']
        self.gateway = subnet['gateway']
        if 'cidr' in subnet:
            self.cidr = subnet['cidr']
        else:
            self.cidr = Subnet.getPrefix(self.netmask)
        
        self.addressSpace = SubnetAddressSpace.getType(subnet['addressSpace']) if 'addressSpace' in subnet else None
        self.type = SubnetType.getType(subnet['subnetType']) if 'subnetType' in subnet else None

    def toJson(self):
        outDict = self.__dict__.copy()
        for k,v in outDict.items():
            if isinstance(v,BaseEnum):
                outDict[k] = v.value

        return json.dumps(outDict)

    def __str__(self):
        return "Subnet %s" % self.__dict__
    def __repr__(self):
        return "Subnet %s" % self.__dict__
    def __eq__(self, other):
        """Equals function for Subnet.  Returns true if the network and cidr are the same."""
        if isinstance(other, self.__class__):
            return self.network == other.network and self.cidr == other.cidr
        else:
            return False
    def __ne__(self, other):
        return not self.__eq__(other)

class VLAN:
    """Entity that represents a softlayer VLAN"""
    # MASK = "id,name,vlanNumber,primaryRouter[datacenter[name]],subnets[" + Subnet.MIN_MASK + "]"
    MASK = "id,name,vlanNumber,primaryRouter[datacenter[name]],subnets[" + Subnet.MASK + "]"
    def __init__(self, detail,subnetType=SubnetType.Any, addressSpace=SubnetAddressSpace.Any):
        self.name = detail['name'] if 'name' in detail else None
        self.id = detail['id']
        self.vlanNumber = detail['vlanNumber']
        self.dataCenter = detail['primaryRouter']['datacenter']['name']

        self.subnets = []
        # print( "vlan details: \n%s" % json.dumps(detail))
        for slSubnet in detail['subnets']:
            subnet = Subnet(slSubnet)
            matchedType = (subnetType == SubnetType.Any or subnetType == subnet.type)
            matchedAddressSpace = (addressSpace == SubnetAddressSpace.Any or addressSpace == subnet.addressSpace)
            if matchedType and matchedAddressSpace:
                # print("** Adding subnet(%s): [addressSpace=%s][subnetType=%s]" % (subnet.id, subnet.addressSpace,subnet.type))
                self.subnets.append(subnet)
    def __repr__(self):
        return "VLAN %s" % self.__dict__

class DeviceType(BaseEnum):
    BareMetal = "BareMetal"
    VM = "VirtualMachine"
    Any = "Any"

class Device:
    MASK = "id,hostname,domain,primaryBackendIpAddress,operatingSystem[passwords[username,password]],tagReferences[tag[name]],networkComponents[primarySubnet[" + Subnet.MASK + "]]"
    def __init__(self, detail):
        # print( "Device as json:\n%s" % json.dumps(detail))
        self.id = detail['id']
        self.hostname = detail['hostname']
        self.domain = detail['domain']
        self.ip = detail['primaryBackendIpAddress']
        self.userid = 'root'
        self.password = [cred['password'] for cred in detail['operatingSystem']['passwords'] if cred['username'] == self.userid][0]
        self.tags = []
        if detail['tagReferences']:
            for tagRef in detail['tagReferences']:
                if 'tag' in tagRef:
                    self.tags.append(tagRef['tag']['name'])

        for obj in detail['networkComponents']:
            if obj['name'] == 'eth' and obj['port'] == 0:
                self.mac = obj['macAddress']
                #self.subnet = Subnet(obj['primarySubnet'])
                self.subnet = obj['primarySubnet']['id']
                break
        # print(self.__dict__)

    def toJson(self):
        return json.dumps(self.__dict__)
    def __str__(self):
        print( "in __str__")
        return "Device %s" % self.__dict__
    def __repr__(self):
        return "Device %s" % self.__dict__
    def __eq__(self, other):
        """Equals function for Subnet.  Returns true if the ids are the same."""
        if isinstance(other, self.__class__):
            return self.id == other.id
        else:
            return False
    def __ne__(self, other):
        return not self.__eq__(other)

class SoftLayerHelper:
    """Wrapper around the softlayer API"""

    @staticmethod
    def getSoftLayerClient(userid=None, apikey=None):
        if userid is None:
            if 'SL_USER' in os.environ:
                userid = os.environ['SL_USER']
        if apikey is None:
            if 'SL_APIKEY' in os.environ:
                userid = os.environ['SL_APIKEY']
        
        if userid is None and apikey is None:
            client = SoftLayer.create_client_from_env()
        else:
            client = SoftLayer.create_client_from_env(userid, apikey)
    
        return client

    def __init__(self, userid=None, apikey=None):
        self.client = self.getSoftLayerClient(userid, apikey)
        self.nwmgr = SoftLayer.NetworkManager(self.client)
        self.hwmgr = SoftLayer.HardwareManager(self.client)

    def getClient(self):
        return self.client
    
    def getDeviceById(self, id):
        return Device(self.hwmgr.get_hardware(id,mask=Device.MASK))
    
    def getDeviceByHostname(self, hostname, deviceType=DeviceType.BareMetal, datacenter=None):
        devices = self.getDevicesByHostname([hostname], deviceType=deviceType, datacenter=datacenter)

        if devices:
            if len(devices) == 1:
                return devices[0]
            elif len(devices) > 1:
                ids = []
                for device in devices:
                    ids.append(device.id) 
                raise Exception("More than one device found with hostname '%s'. Device ids: %s" % (hostname, ', '.join(ids)))
        return None

    def getDevicesByHostname(self, hostname, deviceType=DeviceType.Any, datacenter=None):
        hostnames = []
        if isinstance(hostname, str):
            # hostname is string
            hostnames.append(hostname)
        elif isinstance(hostname, list):
            # hostname is list of hostnames
            hostnames = hostname
        else:
            raise Exception( "Unexpected type for 'hostname' parameter: %s" % hostname.__class__)
        
        result = []
        # for deviceTag in tags:
        if deviceType == DeviceType.BareMetal or deviceType == DeviceType.Any:
            # Look for baretal devices
            filter = {
                'hardware': {
                    'hostname': {
                        'operation': 'in',
                        'options': [{
                            'name': 'data',
                            'value': hostnames
                        }]
                    }
                }
            }
            if datacenter is not None:
                filter['hardware']['datacenter'] = {
                    'name': {
                        'operation': datacenter
                    }
                }
            # slResult = self.client.call('Account', 'getHardware', filter=filter, mask=Device.MASK)
            slResult = self.hwmgr.list_hardware(filter=filter, mask=Device.MASK)
            if len(slResult) > 0:
                for dev in slResult:
                    result.append(Device(dev))
                    # print("Dev: \n%s" %  json.dumps(dev))
            # else:
            #     print("No BM results.")
        if deviceType == DeviceType.VM or deviceType == DeviceType.Any:
            # Look for virtual devices
            filter = {
                'virtualGuests': {
                    'hostname': {
                        'operation': 'in',
                        'options': [{
                            'name': 'data',
                            'value': hostnames
                        }]
                    }
                }
            }
            if datacenter is not None:
                filter['virtualGuests']['datacenter'] = {
                    'name': {
                        'operation': datacenter
                    }
                }
            slResult = self.client.call('Account', 'getVirtualGuests', filter=filter, mask=Device.MASK)
            if len(slResult) > 0:
                for dev in slResult:
                    result.append(Device(dev))
            # else:
            #     print("No results.")
        return result if len(result) > 0 else None                    


    def getDevicesByTag(self, tag, deviceType=DeviceType.Any, datacenter=None):
        tags = []
        if isinstance(tag, str):
            # Tag is string
            tags.append(tag)
        elif isinstance(tag, list):
            # Tag is list of tag
            tags = tag
        else:
            raise Exception( "Unexpected type for 'tag' parameter: %s" % tag.__class__)
        
        result = []
        # for deviceTag in tags:
        if deviceType == DeviceType.BareMetal or deviceType == DeviceType.Any:
            # Look for baretal devices
            filter = {
                'hardware': {
                    'tagReferences': {
                        'tag': {
                            'name': {
                                'operation': 'in',
                                'options': [{
                                    'name': 'data',
                                    'value': tags
                                }]
                            }
                        }
                    }
                }
            }
            if datacenter is not None:
                filter['hardware']['datacenter'] = {
                    'name': {
                        'operation': datacenter
                    }
                }
            slResult = self.client.call('Account', 'getHardware', filter=filter, mask=Device.MASK)
            if len(slResult) > 0:
                for dev in slResult:
                    result.append(Device(dev))
                    # print("Dev: \n%s" %  json.dumps(dev))
            # else:
            #     print("No BM results.")


        if deviceType == DeviceType.VM or deviceType == DeviceType.Any:
            # Look for virtual devices
            filter = {
                'virtualGuests': {
                    'tagReferences': {
                        'tag': {
                            'name': {
                                'operation': 'in',
                                'options': [{
                                    'name': 'data',
                                    'value': tags
                                }]
                            }
                        }
                    }
                }
            }
            if datacenter is not None:
                filter['virtualGuests']['datacenter'] = {
                    'name': {
                        'operation': datacenter
                    }
                }
            slResult = self.client.call('Account', 'getVirtualGuests', filter=filter, mask=Device.MASK)
            if len(slResult) > 0:
                for dev in slResult:
                    result.append(Device(dev))
            # else:
            #     print("No results.")

        return result if len(result) > 0 else None                    


    def getVlans(self, subnetType=SubnetType.Any, addressSpace=SubnetAddressSpace.Any):
        slVlans = self.nwmgr.list_vlans()
        vlans = []
        for vlan in slVlans:
            vlans.append(self.getVlan(vlan['id'],subnetType, addressSpace))
        return vlans

    def getVlan(self, idOrName, subnetType=SubnetType.Any, addressSpace=SubnetAddressSpace.Any):
        if idOrName is None:
            raise Exception("No idOrName specified.")
        vlan = None
        if isinstance(idOrName, numbers.Number):
            vlan = self.nwmgr.get_vlan(idOrName)
        elif isinstance(idOrName, str):
            slVlans = self.nwmgr.list_vlans(name=idOrName,mask=VLAN.MASK)
            vlan = self.nwmgr.get_vlan(slVlans[0]['id']) if len(slVlans) else None
        else:
            raise Exception( "Unexpected type for 'idOrName' parameter: %s" % idOrName.__class__ )
        
        return VLAN(vlan, subnetType=subnetType, addressSpace=addressSpace) if vlan else None

    def getSubnetForIP(self, ip):
        subnetHelper = self.client['SoftLayer_Network_Subnet']
        subnet = subnetHelper.getSubnetForIpAddress(ip,mask=Subnet.MASK)

        return Subnet(subnet)
        # print( "Result type %s:\n%s" % (subnet.__class__, subnet))

    def findIpByNoteInSubnet(self, id, note):
        mask='id,ipAddress,isReserved,note'
        filter = {
            'ipAddresses': {
                'note': {'operation': note}
            }
        }
        subnetHelper = self.client['SoftLayer_Network_Subnet']
        result = subnetHelper.getIpAddresses(id=id,filter=filter,mask=mask)

        if len(result) == 0:
            return None
        if len(result) == 1:
            return result[0]['ipAddress']
        else:
            raise Exception("More than one IP found with this note text: %s" % note )

    def findIpInfoByNoteInVlan(self, idNameOrVlan, note, subnetType=SubnetType.Any, addressSpace=SubnetAddressSpace.Any):
        if isinstance(idNameOrVlan, numbers.Number) or isinstance(idNameOrVlan, str):
            searchVlan = self.getVlan(idNameOrVlan, subnetType=subnetType, addressSpace=addressSpace)
        elif isinstance(idNameOrVlan, VLAN):
            searchVlan = idNameOrVlan
        else:
            raise Exception( "Unexpected type for vlan param.  Expected, VLAN id or name or VLAN object")
        if searchVlan:
            result_ips = []
            result_subnets = []
            for subnet in searchVlan.subnets:
                ip = self.findIpByNoteInSubnet(subnet.id, note)
                if ip:
                    result_ips.append(ip)
                    result_subnets.append(subnet)
            if len(result_ips) == 0:
                return None,None
            elif len(result_ips) == 1:
                return result_ips[0], result_subnets[0]
            else:
                raise Exception( "More than one IP found with note: %s" % note )
        return None            
