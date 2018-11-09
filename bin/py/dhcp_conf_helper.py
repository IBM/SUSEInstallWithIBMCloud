from collections import Sequence
from utils import tokenize, stringToFile, BaseEnum

class DhcpConfEntryType(BaseEnum):
    """
    Enumeration for the types of sections processed in a dhcpd.conf file.
    
    Current sections supported:
      - shared-network
      - subnet
      - group
      - host
    """
    Shared_Network='shared-network' 
    Subnet="subnet"
    Host="host"
    Group="group"

class DhcpConfEntry:
    """
    Class to represent a section in the dhcp conf. The types of entries supported are
    those defined by the DhcpConfEntryType enumeration, i.e. :
     - shared network
     - subnet
     - group
     - host

     The entry maintains:
      - a list of child entries per type (DhcpConfEntry) 
      - a list of the lines contained in the entry

    You can search, add and remove immediate child entries based on either type and/or name, or by an entry
    """
    def __init__(self, type, sectionName=None, parent=None, startLine=None, endLine='}'):
        """
        Constructor for DhcpConfEntry.

         @type type: DhcpConfEntryType
         @param type: the type of entry to create

         @type sectionName: str
         @param sectionName: the name of the section (optional)

         @type parent: DhcpConfEntry
         @param parent: the parent entry (optional)

         @type startLine: str
         @param startLine: the text of the starting line of the section

         @type endLine: str
         @param endLine: the text of the end of the section.  Defaults to '}'
        """
        self.type = type
        self.name = sectionName
        self.parent = parent
        self.children = {}
        self.lines = []
        self.start = startLine
        self.end = endLine

    def __str__(self):
        """To string representation"""
        # return "Subnet{ identifier: '%s/%s', netmask: '%s', broadcast: '%s', gateway: '%s' }" % ( self.ip, self.prefix, self.netmask, self.broadcast, self.gateway)
        return "DhcpConfEntry %s" % self.__dict__
    def __eq__(self, other):
        """Equals function for DhcpConfEntry.  Returns true if the type and start line are the same."""
        if isinstance(other, self.__class__):
            return self.type == other.type and self.start == other.start
        else:
            return False
    def __ne__(self, other):
        return not self.__eq__(other)

    def addChild(self,entry):
        """
        Add a child entry.  It uses the type in the entry to determine where to add the entry
        """
        key = entry.type.name
        if key not in self.children:
            self.children[key] = []
        # Set the parent for the new entry
        entry.parent = self
        # Add the entry
        self.children[key].append(entry)
    
    def addLine(self,line):
        self.lines.append(line)

    def removeChild(self, type, name=None):
        if not type:
            return False
        key = type.name
        child = self.findChild(type, name)
        if child:
            child.parent.children[key].remove(child)
            return True
        return False

    def removeChildEntry(self, entry):
        if not entry or not entry.type:
            return False
        key = entry.type.name
        child = self.findChild(entry.type, entry.name)
        if child:
            child.parent.children[key].remove(child)
            return True
        return False

    def getFirstChild(self, typeOrName): #, name=None):
        if isinstance(typeOrName, DhcpConfEntryType):
            key = typeOrName.name
        elif isinstance(typeOrName, str):
            key = typeOrName
        if key in self.children:
            return self.children[key][0]
        return None

    def contains(self, typeOrName, name):
        childEntry = self.findChild(typeOrName, name)

        return childEntry != None
    
    def containsEntry(self, entry):
        if entry:
            childEntry = self.findChildEntry(entry)
            return childEntry != None
        return None

    def findChildEntry(self, entry):
        """
        Find a child entry, by searching the list of same type entries

        @type entry: DhcpConfEntry
        @param entry: the entry to look for in the child entries
        """
        if entry:
            return self.findChild(entry.type, entry.name)
        return None

    def getChildren(self, typeOrName):
        if isinstance(typeOrName, DhcpConfEntryType):
            key = typeOrName.name
        elif isinstance(typeOrName, str):
            key = typeOrName
        return self.children[key] if key in self.children else None
    
    def findChild(self, typeOrName, name=None):
        if isinstance(typeOrName, DhcpConfEntryType):
            key = typeOrName.name
        elif isinstance(typeOrName, str):
            key = typeOrName
        if key in self.children:
            # print("self.children[key]: %s" % self.children[key])
            for child in self.children[key]:
                # print("[Child is %s]" % child.__class__)
                # print("[Child is %s]" % child.toText())
                if child.name == name:
                    # print( "Found child type %s: %s" % (child.__class__, child.toText()))
                    return child
        return None

    def toText(self, indent=""):
        levelIndent = "  "
        result = ""

        if self.start:
            result += self.start + '\n'
        for line in self.lines:
            result += indent + line + '\n'
        for childTypeName in self.children:
            entries = self.children[childTypeName]
            for child in entries:
                result += indent + child.toText(indent + levelIndent) + '\n'
        if self.end:
            # hasParent = "YES" if self.parent else "NO"
            # hasGrandParent = "YES" if self.parent and self.parent.parent else "NO"
            # result += "(hasParent=%s)(hasGrandParent=%s)\n" % (hasParent, hasGrandParent)
            if self.parent and self.parent.parent:
                result += levelIndent + self.end #+ '\n'
            else:
                result += self.end #+ '\n'
        return result

class DhcpConfHelper:
    """Class to help with reading and writing the dhcp.conf file"""

    def __init__(self, filename=None):
        self.top = DhcpConfEntry(None, None, endLine=None)
        self.filename = filename
        if filename:
            self.readFile(filename)

    def getFilename(self):
        return self.filename

    def getRootEntry(self):
        return self.top
    
    def getSharedNetworks(self):
        return self.top.getFirstChild(DhcpConfEntryType.Shared_Network)
    
    def getGroup(self):
        return self.top.findChild(DhcpConfEntryType.Group)

    @staticmethod
    def fromFile(confFile):
        return DhcpConfHelper().readFile(confFile)
    
    @staticmethod
    def fromText(textOrList):
        return DhcpConfHelper().readText(textOrList)

    def readFile(self, confFile):
        """
        Read a "dhcpd.conf" type specified by the confFile

         @type confFile: str
         @param confFile: the path to the file containing dhcpd.conf structure
        """
        with open(confFile) as file:
            self.readText(file.readlines())
        return self
    
    def readText(self, textOrList):
        if isinstance(textOrList,str):
            lines = textOrList.splitlines()
        elif isinstance(textOrList,list):
            lines = textOrList
        else:
            raise Exception("Dont know how to process type '%s'. Expected either text or list of strings." % textOrList.__class__)

        currEntry = self.top
        interestedIn = DhcpConfEntryType.getTypes() #[ 'subnet', 'shared-network', 'group', 'host' ]
        
        for line in lines:
            # Remove anything passed a '#'
            strippedLine = line.strip().split('#')[0]
            # if !strippedLine.startswith("#") and strippedLine != "":
            if strippedLine != "":
                # split and stip extra spaces from the line
                tokens = tokenize(strippedLine)

                # Check first token to see if it a section start, i.e. keyword: shared-network, group, subnet, host,
                if tokens[0] in interestedIn:
                    # Means a new section is starting. Now determine the type
                    type = DhcpConfEntryType.getType(tokens[0])
                    if type is None:
                        raise Exception( "Dont know how to deal with this section '%s' of line: %s" % (tokens[0], line) )
                    # Check that the open brace, "{" is found in the line
                    if '{' not in tokens:
                        raise Exception( "Detected section '%s' but no trailing { found: %s" % (tokens[0], line ) )
                    # Now the name if any specified
                    name = None
                    if tokens[1] != '{':
                        name = tokens[1]
                    # Now that we have type, name and have verified it is ok, we create the new entry
                    newEntry = DhcpConfEntry(type, name, startLine=' '.join(tokens))
                    # newEntry = DhcpConfEntry(type, name, currEntry, startLine=' '.join(tokens), endLine='}')
                    # Added into the chain
                    currEntry.addChild(newEntry)
                    # Make it the current entry
                    currEntry = newEntry
                elif tokens[0] == '}':
                    # ending a token, so set current to the parent.
                    currEntry = currEntry.parent
                else:
                    currEntry.addLine(' '.join(tokens))
        if currEntry != self.top:
            raise Exception( "Section '%s' does not seem to have closed: %s" % (currEntry.type.value[0], currEntry.start))
        return self
    
    def toText(self):
        return self.top.toText()
    def writeFile(self, confFile):
        stringToFile(confFile, self.toText())
    
    def save(self):
        if self.filename:
            stringToFile(self.filename, self.toText())
            return True
        return False
