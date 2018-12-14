import os
import yaml
import io
from utils import ipToHex
from templates import Templates

REQ_IMAGE_FIELDS = [ 'name', 'file_url', 'filename', 'save_dir', 'mount_point']
REQ_MACHINE_FIELDS = ['tag','image','yast_template']


class Config:
    'Class to load and read from image and machine configuration'

    #
    # Validate dictionary object
    #
    @staticmethod
    def validateRequiredFields(obj, reqFields, type):
        for f in reqFields:
            if f not in obj:
                raise Exception( "Missing field '%s' from type '%s': %s" % (f, type, obj) )
    #
    # Constructor
    #
    def __init__(self, filename, bootserverIP):
        with io.open( filename, 'r') as stream:
            data = yaml.load(stream)
        # Read data from the 'conf' section
        if 'conf' not in data:
            raise Exception("Section 'conf' missing from the config file.")
        if 'http_root_dir' not in data['conf']:
            raise Exception("Property 'conf.http_root_dir' missing from the config file.")
        self.httpRootDir = data['conf']['http_root_dir']

        # Read data from the 'vlan' section
        if 'vlan' not in data or ('name' not in data['vlan'] and 'id' not in data['vlan']):
            raise Exception("No VLAN information found in config.")
        # if 'name' not in data['vlan'] and 'id' not in data['vlan']
        if 'id' in data['vlan']:
            self.vlanIdOrName = data['vlan']['id']
        elif 'name' in data['vlan']:
            self.vlanIdOrName = data['vlan']['name']

        # Check if the 'images' and 'machines' sections are there in the config
        if 'images' not in data:
            raise Exception("No 'images' section found in config: %s" % filename )
        elif 'machines' not in data:
            raise Exception("No 'machines' section found in config: %s" % filename )
        
        self.templatesDir = os.path.dirname(os.path.realpath(__file__)) + '/templates/'
        self.yastTemplatesDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)) + "/../../yast_templates" )
        self.baseVars = { 'bootserverIP': bootserverIP, 'http_root_dir': self.httpRootDir }
        self.images = {}
        self.machines = {}

        # Read the 'images' section
        for v in data['images']:
            self.validateRequiredFields(v, REQ_IMAGE_FIELDS, 'image')
            # v['bootserverIP'] = bootserverIP
            self.images[v['name']] = v
        
        # Read the 'machines' section
        for v in data['machines']:
            self.validateRequiredFields(v, REQ_MACHINE_FIELDS, 'image')
            if self.getImage(v['image'], False):
                # v['bootserverIP'] = bootserverIP
                self.machines[v['tag']] = v
            else:
                raise Exception("Machine '%s' is referencing an undefined image: %s" % (v['tag'], v['image']))
    
    def expandTemplates(self, genDir, template, outFileMask, filenameProp, objects, objectName, baseVars=None  ):
        for item in objects.values():
            print( "Expanding template '%s' for: %s" % (template, item[filenameProp]))

            vars = baseVars.copy() if baseVars else {}
            vars['GEN_DIR'] = genDir
            
            for k in item:
                vars[objectName+"_"+k] = item[k]

            Templates.mergeToFile(self.templatesDir + template, outFileMask.format(item[filenameProp]), vars )
    #
    # Get available image names
    #
    def getImageNames(self):
        result = []
        for k in self.images:
            result.append(k)
        return result

    #
    # Get all images
    #
    def getImages(self):
        result = []
        for v in self.images.values():
            result.append(v)
        return result

    #
    # Get a specific image
    # Throws KeyError is no such image found.
    #
    def getImage(self, name, raiseError=True):
        return None if name not in self.images and not raiseError else self.images[name]

    #
    # check if an md5 file url has been defined for an image.
    #
    def imageHasMD5Url(self, name):
        image = self.getImage(name, False)
        return True if image and 'md5_url' in image else False

    #
    # check if an md5 value has been specified for an image.
    #
    def imageHasMD5Value(self, name):
        image = self.getImage(name, False)
        return True if image and 'md5_value' in image else False

    #
    # Get the available machine types
    #
    def getMachineTags(self):
        result = []
        for k in self.machines:
            result.append(k)
        return result

    #
    # Get all the machine tag definitions
    #
    def getMachines(self):
        result = []
        for v in self.machines.values():
            result.append(v)
        return result
    #
    # Get the info for a specific tag
    #
    def getMachine(self,tag, raiseError=True):
        return None if tag not in self.machines and not raiseError else self.machines[tag]

    def machineHasPostInstall(self,tag):
        machine = self.getMachine(tag,False)
        return True if machine and 'post_install_scripts' in machine else False
    
    def generateDownloadScripts(self, genDir):
        self.expandTemplates(genDir, 'tftp/download_image.sh', genDir +"/download_image_{}.sh", 'name', self.images, 'image', self.baseVars )
    
    def generateConfigForTFTP(self, genDir):
        self.expandTemplates(genDir, 'tftp/pxelinux_cfg_default_for_image.txt', genDir +"/default_for_{}", 'name', self.images, 'image', self.baseVars)
        self.expandTemplates(genDir, 'tftp/boot_msg_for_image.txt', genDir +"/boot_msg_for_{}", 'name', self.images, 'image', self.baseVars)
        self.expandTemplates(genDir, 'tftp/setup_tftp_for_image.sh', genDir +"/setup_tftp_for_{}.sh", 'name', self.images, 'image', self.baseVars)
        Templates.mergeToFile(self.templatesDir + 'tftp/mount_image.sh', genDir + '/mount_image.sh', { })

    def generateDhcpSubnetEntryText(self, vars):
        return Templates.mergeToString(self.templatesDir + 'dhcp/dhcp_subnet_template.txt',vars)
    
    def generateDhcpHostEntryText(self, vars):
        return Templates.mergeToString(self.templatesDir + 'dhcp/dhcp_host_template.txt',vars)

    def generateAutoyastFile(self, autoyastTemplate, autoyastOutFilename, vars):
        outFile = "%s/autoyast/%s" % (self.httpRootDir, autoyastOutFilename)
        Templates.mergeToFile(self.yastTemplatesDir + autoyastTemplate, outFile, vars)
        return outFile
    
# Reboot baremetal:
#  slcli hardware list | grep kvmhost | awk '{print $1}' | xargs -I % slcli -y hardware reboot --soft  %
