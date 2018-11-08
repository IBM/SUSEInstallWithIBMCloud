import os
import binascii
import struct
import socket
from aenum import Enum

class BaseEnum(Enum):
    def __str__(self):
        return self.value
    def __repr__(self):
        return self.value
    @classmethod
    def getType(cls,value):
        for _, member in cls.__members__.items():
            if member.value == value:
                return member
        raise Exception("Unknown enum for class %s: %s" % (cls.__name__, value) )
    @classmethod
    def getTypes(cls):
        """
        Returns a list of strings with the values of the enums
        
         @rtype list: list with the possible values
        """ 
        result = []
        for _, member in cls.__members__.items():
            result.append(member.value)
        return result

def tokenize(line):
    tokens = line.split(' ')

    outTokens = []
    for token in tokens:
        stripped = token.strip()
        if stripped != "":
            outTokens.append(stripped)
    
    return outTokens

def fileToString(filename):
    """Read a file into a string.  Closes the input file stream."""
    open(filename,'r').read()
    try:
        with open(filename,'r') as stream:
            return stream.read()
    finally:
        stream.close()

def stringToFile(filename, string):
    """Write a string to a file."""
    try:
        outFile = open(filename, "w")
        outFile.write(string)
    finally:
        outFile.close()

def aton(addr):
    return struct.unpack('!I', socket.inet_aton(addr))[0]

def ntoa(n):
    return socket.inet_ntoa(struct.pack('!I', n))

def ipToHex(ip):
    return binascii.hexlify(socket.inet_aton(ip)).upper()

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def restartDHCP():
    print("Restarting DHCP Daemon...")
    exitStatus = os.system("systemctl restart dhcpd")
    # exitStatus = 0
    print("Restarted DHCP Daemon. Exit status: %s" % exitStatus)
    return exitStatus

def restartDevice(deviceId):
    print("Initiate restart of device with id: %s ..." % deviceId)
    exitStatus = os.system("slcli -y hardware reboot --soft %s" % deviceId)
    # exitStatus = 0
    print("Restart initiated. Exit status: %s" % exitStatus)
    return exitStatus
