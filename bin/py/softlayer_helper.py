import os
import SoftLayer
import numbers
from baseobj import BaseEnum, BaseObject, JsonSerializable

class SoftLayerHelperException(Exception):
    """ Base exception """
    def __init__(self, msg):
        self.msg = msg
    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.msg)

    def __str__(self):
        return '%s: %s' % (self.__class__.__name__, self.msg)

class ObjectNotFoundException(SoftLayerHelperException):
    """ General object not found exception """

class MoreThanOneMatchFoundException(SoftLayerHelperException):
    """ Exception raised when more than one match found """

class IpAddress(BaseObject, JsonSerializable):
    """ 
        Represents an ip address 
    """
    MASK = 'isNetwork, isBroadcast, isGateway, ipAddress, id, isReserved,virtualGuest,hardware,note,subnetId'
    class Status(BaseEnum):
        Reserved = "Reserved"
        In_Use = "In Use"
        Other = "Other"
        # Unknown = "Unknown"
    class Type(BaseEnum):
        Network = "Network"
        Gateway = "Gateway"
        Broadcast = "Broadcast"
        Reserved = "Reserved"
        VirtualDevice = "Virtual Device"
        HardwareDevice = "Hardware Device"
        UserDefined = "User-defined"
        # Unspecified = "Unspecified"
    def __init__(self, data):
        #id,ipAddress,isReserved,note
        self.id = data['id']
        self.subnetId = data['subnetId']
        self.value = data['ipAddress']
        # self.reserved = data['isReserved']
        self.note = data['note'] if 'note' in data else None
        # self.status = self.Status.Unknown
        # self.type = self.Type.Unspecified
        self.status = self.Status.Other
        self.type = self.Type.UserDefined
        if data['isNetwork']:
            self.status = self.Status.Reserved
            self.type = self.Type.Network
        elif data['isBroadcast']:
            self.status = self.Status.Reserved
            self.type = self.Type.Broadcast
        elif data['isGateway']:
            self.status = self.Status.Reserved
            self.type = self.Type.Gateway
        elif data['isReserved']:
            self.status = self.Status.Reserved
            self.type = self.Type.Reserved
        else:
            try: 
                self.hostname = data['virtualGuest']['fullyQualifiedDomainName']
                self.status = self.Status.In_Use
                self.type = self.Type.VirtualDevice
            except KeyError:
                pass
            try:
                self.hostname = data['hardware']['fullyQualifiedDomainName']
                self.status = self.Status.In_Use
                self.type = self.Type.HardwareDevice
            except KeyError:
                pass

# class Subnet():
class Subnet(BaseObject, JsonSerializable):
    class AddressSpace(BaseEnum):
        Public = "PUBLIC"
        Private = "PRIVATE"
        Any = "Any"
    class Type(BaseEnum):
        Primary = "ADDITIONAL_PRIMARY"
        Portable = "SECONDARY_ON_VLAN"
        Primary_IPV6 = "PRIMARY_6"
        Any = "Any"
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
        self.name = "{}/{}".format(self.network, self.cidr)
        
        self.addressSpace = self.AddressSpace.getType(subnet['addressSpace']) if 'addressSpace' in subnet else None
        self.type = self.Type.getType(subnet['subnetType']) if 'subnetType' in subnet else None

    def __eq__(self, other):
        """Equals function for Subnet.  Returns true if the network and cidr are the same."""
        if isinstance(other, self.__class__):
            return self.network == other.network and self.cidr == other.cidr
        else:
            return False
    def __ne__(self, other):
        return not self.__eq__(other)

class VLAN(BaseObject, JsonSerializable):
    """Entity that represents a softlayer VLAN"""
    # MASK = "id,name,vlanNumber,primaryRouter[datacenter[name]],subnets[" + Subnet.MIN_MASK + "]"
    MASK = "id,name,vlanNumber,primaryRouter[datacenter[name]],subnets[" + Subnet.MASK + "]"
    def __init__(self, detail,subnetType=Subnet.Type.Any, addressSpace=Subnet.AddressSpace.Any):
        self.name = detail['name'] if 'name' in detail else None
        self.id = detail['id']
        self.vlanNumber = detail['vlanNumber']
        self.dataCenter = detail['primaryRouter']['datacenter']['name']

        self.subnets = []
        for slSubnet in detail['subnets']:
            subnet = Subnet(slSubnet)
            matchedType = (subnetType == Subnet.Type.Any or subnetType == subnet.type)
            matchedAddressSpace = (addressSpace == Subnet.AddressSpace.Any or addressSpace == subnet.addressSpace)
            if matchedType and matchedAddressSpace:
                # print("** Adding subnet(%s): [addressSpace=%s][subnetType=%s]" % (subnet.id, subnet.addressSpace,subnet.type))
                self.subnets.append(subnet)

class NetworkGateway(BaseObject, JsonSerializable):
    MASK = "privateVlanId,publicVlanId,name,publicIpAddressId,accountId,networkSpace,id,privateIpAddressId"
    """
        This class represents the NetworkGateway (vyatta)
    """
    class NetworkSpace(BaseEnum):
        Private = "PRIVATE"
        Both = "BOTH"

    def __init__(self, data, slHelper):
        """
            sample data:
            {
                'privateVlanId': 2403029,            <-- self.privateVlanId
                'publicIpv6AddressId': 117415697, 
                'publicVlanId': 2403031,             <-- self.publicVlanId
                'name': 'dal13-ded-1698663x1-01-a',  <-- self.name
                'groupNumber': 1, 
                'statusId': 1, 
                'publicIpAddressId': 117415683,      <-- self.publicIP (as IP after looking it up using the id)
                'accountId': 1698663,                <-- self.account
                'networkSpace': 'BOTH',              <-- self.networkSpace
                'id': 395403,                        <-- self.id
                'privateIpAddressId': 117413749      <-- self.privateIP (as IP after looking it up using the id)
            }
        """
        self.name = data['name'] #if 'name' in data else None
        self.privateVlanId = data['privateVlanId'] #if 'privateVlanId' in data else None
        self.publicVlanId = data['publicVlanId']
        self.account = data['accountId']
        self.id = data['id']
        self.networkSpace = self.NetworkSpace.getType(data['networkSpace'])
        self.publicIP = slHelper.findIpById(data['publicIpAddressId'])
        self.privateIP = slHelper.findIpById(data['privateIpAddressId'])

class Device(BaseObject, JsonSerializable):
    class Type(BaseEnum):
        BareMetal = "BareMetal"
        VM = "VirtualMachine"
        Any = "Any"
    MASK = "id,hostname,domain,primaryBackendIpAddress,operatingSystem[passwords[username,password]],tagReferences[tag[name]],networkComponents[primarySubnet[" + Subnet.MASK + "]]"
    def __init__(self, detail):
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
    @staticmethod
    def isAPIError_ObjNotFound(softLayerAPIError):
        if isinstance(softLayerAPIError, SoftLayer.SoftLayerAPIError):
            return True if softLayerAPIError.faultCode == 'SoftLayer_Exception_ObjectNotFound' else False
        return False


    def __init__(self, userid=None, apikey=None):
        self.client = self.getSoftLayerClient(userid, apikey)
        self.nwmgr = SoftLayer.NetworkManager(self.client)
        self.hwmgr = SoftLayer.HardwareManager(self.client)

    def getClient(self):
        return self.client
    
    def getDeviceById(self, id):
        return Device(self.hwmgr.get_hardware(id,mask=Device.MASK))
    
    def getDeviceByHostname(self, hostname, deviceType=Device.Type.BareMetal, datacenter=None):
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

    def getDevicesByHostname(self, hostname, deviceType=Device.Type.Any, datacenter=None):
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
        if deviceType == Device.Type.BareMetal or deviceType == Device.Type.Any:
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
        if deviceType == Device.Type.VM or deviceType == Device.Type.Any:
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


    def getDevicesByTag(self, tag, deviceType=Device.Type.Any, datacenter=None):
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
        if deviceType == Device.Type.BareMetal or deviceType == Device.Type.Any:
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

        if deviceType == Device.Type.VM or deviceType == Device.Type.Any:
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

    def attachVlansToNetworkGateway(self, gatewayId, vlanIds, bypass):
        """
            Attach a VLAN to a network gateway (vyatta).  If "bypass" is True when VLAN is bypassed, otherwise it is routed through the gateway.
        """
        vlans = []

        for vlanId in vlanIds:
            vlanData = {
                # 'id': None
                'bypassFlag': bypass,
                'networkGatewayId' : gatewayId,
                'networkVlanId': vlanId
            }
            vlans.append(vlanData)

        try:
            self.client['Software_Network_Gateway_Vlan'].createObject(vlans)
            return True
        except:
            return False

    def getVlans(self, subnetType=Subnet.Type.Any, addressSpace=Subnet.AddressSpace.Any):
        """
            Retrieve a list of VLANs. Optionally, filter the type of subnets included in each VLAN.
        """
        slVlans = self.nwmgr.list_vlans()
        vlans = []
        for vlan in slVlans:
            vlans.append(self.getVlan(vlan['id'],subnetType, addressSpace))
        return vlans if len(vlans) > 0 else None

    def getVlan(self, idOrName, subnetType=Subnet.Type.Any, addressSpace=Subnet.AddressSpace.Any):
        try:
            if idOrName is None:
                raise Exception("No idOrName specified.")
            vlan = None
            idIsNumber = True
            if isinstance(idOrName, numbers.Number):
                vlan = self.nwmgr.get_vlan(idOrName)
            elif isinstance(idOrName, str):
                idIsNumber = False
                slVlans = self.nwmgr.list_vlans(name=idOrName,mask=VLAN.MASK)
                vlan = self.nwmgr.get_vlan(slVlans[0]['id']) if len(slVlans) else None
            else:
                raise Exception( "Unexpected type for 'idOrName' parameter: %s" % idOrName.__class__ )
            
            return VLAN(vlan, subnetType=subnetType, addressSpace=addressSpace) if vlan else None
        except SoftLayer.SoftLayerAPIError as e:
            if self.isAPIError_ObjNotFound(e):
                raise ObjectNotFoundException("VLAN with {} '{}' not found.".format("id" if idIsNumber else "name", idOrName))
            raise e

    def getSubnetForIP(self, ip):
        subnetHelper = self.client['SoftLayer_Network_Subnet']
        subnet = subnetHelper.getSubnetForIpAddress(ip,mask=Subnet.MASK)

        return Subnet(subnet)

    def findIpById(self, id):
        """
            Retrieve IP by its id.

            If no IP with id is found, then ObjectNotFoundException is raised
        """
        try:
            ipAddrData = self.client['SoftLayer_Network_Subnet_IpAddress'].getObject(id=id,mask=IpAddress.MASK)

            return IpAddress(ipAddrData)
            # return IpAddress(ipAddrData) if ipAddrData else None
        except SoftLayer.SoftLayerAPIError as e:
            if self.isAPIError_ObjNotFound(e):
                raise ObjectNotFoundException("IP with id '{}' not found".format(id))
            raise e

    def findIpByNoteInSubnet(self, id, note):
        """
            Searches in a subnet for an IP with the specified note/comment.

            If the subnet (by id) is found and a matching IP is found, it is returned.

            If no matching IP is found, None is returned.

            If no subnet found by Id, then an ObjectNotFoundException is raised.

            If more than one matching IPs are found, then a MoreThanOneMatchFoundException is raised.
        """
        filter = {
            'ipAddresses': {
                'note': {'operation': note}
            }
        }
        subnetHelper = self.client['SoftLayer_Network_Subnet']
        try:
            result = subnetHelper.getIpAddresses(id=id,filter=filter,mask=IpAddress.MASK)

            if len(result) == 0:
                return None
            if len(result) == 1:
                # return result[0]['ipAddress']
                return IpAddress(result[0])
            else:
                raise MoreThanOneMatchFoundException("More than one IP found with this note text: %s" % note )
        except SoftLayer.SoftLayerAPIError as e:
            if self.isAPIError_ObjNotFound(e):
                raise ObjectNotFoundException("Subnet with id '{}' not found.".format(id))
            raise e

    def setIpNote(self, ip_id, note):
        """
            Set the comment of an IP (by ID).  To clear the note, specify empty string ''.
            Returns True if the comment updated successfully or False otherwise.

            If the IP based on id does not exist, then an ObjectNotFoundException is raised.
 
        """
        ip = {
            'id': ip_id,
            'note': note,
        }
        try:
            return self.client['SoftLayer_Network_Subnet_IpAddress'].editObject(ip,id=ip_id)
            # return True
        except SoftLayer.SoftLayerAPIError as e:
            if self.isAPIError_ObjNotFound(e):
                return False
            raise e

    def getSubnet(self, id):
        """
            Retrieve subnet details based on id.

            If no subnet with specified id is found, then ObjectNotFoundException is raised.
        """
        try:
            subnetData = self.client['SoftLayer_Network_Subnet'].getObject(id=id, mask=Subnet.MASK)
            return Subnet(subnetData) if subnetData else None
        except SoftLayer.SoftLayerAPIError as e:
            if self.isAPIError_ObjNotFound(e):
                raise ObjectNotFoundException("Subnet with id '{}' not found.".format(id))
                # return None
            raise e

    def getIPsInSubnet(self, id, type=None, status=None):
        """
            Retrieve IPs for a subnet. Optionally, filter the IPs by either status and/or type.

            If no subnet with provided id is found, then ObjectNotFoundException is raised.

            If the subnet is found, then either an array of matching IP objects are returned, or None if no matched IPs found.
        """
        subnet = self.client['SoftLayer_Network_Subnet']
        try:
            ips = subnet.getIpAddresses(id=id,mask=IpAddress.MASK)
            result = []
            for ipdata in ips:
                ipAddr = IpAddress(ipdata)
                if (type == None or ipAddr.type == type) and (status == None or ipAddr.status == status):
                    result.append(ipAddr)
            return result if len(result) > 0 else None
        except SoftLayer.SoftLayerAPIError as e:
            if self.isAPIError_ObjNotFound(e):
                raise ObjectNotFoundException("Subnet with id '{}' not found.".format(id))
                # return None
            raise e

    def findIpInfoByNoteInVlan(self, idNameOrVlan, note, subnetType=Subnet.Type.Any, addressSpace=Subnet.AddressSpace.Any):
        """
            Searches for an ip in a vlan (by name,id or vlan object) based on its "comment" on particular subnet 
            type (portable, private, etc) and particular address space (public, private, etc)

            Returns the IP and the subnet it is in.

            If the VLAN cannot be found by name or id, then an ObjectNotFoundException is raised.

            If no such IP found, it returns None for both IP and subnet

            If more than one IP found with the comment, then a MoreThanOneMatchFoundException is raised.
        """
        if isinstance(idNameOrVlan, numbers.Number) or isinstance(idNameOrVlan, str):
            try:
                searchVlan = self.getVlan(idNameOrVlan, subnetType=subnetType, addressSpace=addressSpace)
            except SoftLayer.SoftLayerAPIError as e:
                if self.isAPIError_ObjNotFound(e):
                    raise ObjectNotFoundException("VLAN with id or name '{}' not found".format(idNameOrVlan))
                    # return None
                raise e
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
                raise MoreThanOneMatchFoundException( "More than one IP found with note: %s" % note )
        return None,None

    def getGatewayAppliance(self, id):
        """
            Retrieve the gateway appliance (vyatta) details by looking up by id.

            If the vyatta is not found then an ObjectNotFoundException is raised.
            If the vyatta is found, then it is returned.
        """
        try:
            gateway = self.client['SoftLayer_Network_Gateway'].getObject(id=id, mask=NetworkGateway.MASK)
            return NetworkGateway(gateway, self)
        except SoftLayer.SoftLayerAPIError as e:
            if self.isAPIError_ObjNotFound(e):
                raise ObjectNotFoundException("Vyatta with id '{}' not found.".format(id))
                # return None
            raise e

    def getGatewayAppliances(self, namePrefix=None):
        """
            Search for gateway appliances (vyattas) by the name prefix.

            Returns an array containing the matching vyattas if at least one match found. 
            
            Returns None if no maches found.
        """
        filter = None
        if namePrefix:
            filter = {
                'name': { 'operation': '^='+namePrefix}
            }
        
        gateways = self.client['SoftLayer_Account'].getNetworkGateways(filter=filter,mask=NetworkGateway.MASK)
        result = []
        if gateways:
            for gatewayData in gateways:
                gateway = NetworkGateway(gatewayData, self)
                if namePrefix is None or gateway.name.startswith(namePrefix):
                    result.append(gateway)
        return result if len(result) > 0 else None

