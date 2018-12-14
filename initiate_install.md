# Bootstrap Scripts

## Libraries

| Script | Purpose |
|--------|---------|
|[dhcp_conf_helper.py](bin/py/dhcp_conf_helper.py)|Utility class for reading and updating DHCP servers' `/etc/dhcp/dhcpd.conf` file.|
|[softlayer_conf_helper.py](bin/py/softlayer_conf_helper.py)|Utility class for interacting with the IBM Cloud API.|
|[templates.py](bin/py/templates.py)|Utility class for doing simple token replacement in files (templates).|
|[config.py](bin/py/config.py)|Utility class for reading the configuration YAML file and providing configuration values to other scripts/classes. Also, provides functions to generate files and configuration entries based on templates files.|
|[notif_handler.py](bin/py/notif_handler.py)|Simple HTTP listener class for handling notifications from hosts that are getting SUSE OS installed.|
|[utils.py](bin/py/utils.py)|Various useful helper functions.|

## Individual Scripts

| Script | Purpose |
|--------|---------|
|[setup_boot_server.sh](bin/setup_boot_server.sh)|Script to configure a VSI to support network booting baremetals.|
|[setup_and_config_host.sh](bin/setup_and_config_host.sh)|Script to configure boot server for serving and remote booting baremetals and also handling SUSE installation on those baremetals.|

## Invocation pre-requisites

Before using the scripts and python code provided by this project, several things need to have taken place. The pre-requisites are:

1. VLAN and subnets (private and portable) must have been ordered on the targeted IBM Cloud account. The VLAN id or name will be needed during the run of the scripts (see later for details).
1. The bare metal machines and boot server VM must also be ordered and provisioned on the IBM Cloud account. The Boot Server VM should be order with Cent OS as the script are written for that Linux OS type.
1. For each bare metal, a "tag" must be specified to identify the "kind" of machine it will be. For example, the tags can be: `kvm`, `compute`, `control`, `pet`, `swift` and `osd`. This tag can be set via the IBM Cloud portal or via API calls. Each bare metal should have only one of these tags.
1. For each bare metal, IP addresses from one of the ordered portable subnets must be "marked" with the hostname of the matching bare metal. Essentially, "marking" means making the "comment" field of the IP to contain the hostname of the desired bare metal.  For example, if a bare metal indended for "kvm" has hostname `kvmhost`, then one of the IPs in one of the portable subnets, will need to have its comment updated to the text `kvmhost`.  This is how the code will retrieve the desired portable IP to use for the bare metal.
1. For each OS image to install, download URLs need to be identified.  You can also include md5 files for the images so that the images can be verified once downloaded by the scripts. You can either specify URLs for MD5 files or specify the MD5 hash inside the config file (see below)

## Preparing the configuration file `config.yaml`

Before running the scripts, a configuration file, e.g. `config.yaml` needs to be created for your setup. The configuration file has basically three sections in it:
- "Config" misc entries, e.g. for directories and VLAN to use
- "Image" entries for each different SUSE ISO image being "offered" for network boot and installation
- "Machine" entries for each "type" (tag) of machine to configure.  Each machine is "tied" with an image to use and a template autoyast file, thus allowing to specify the correct ISO image and autoyast configuration to use during booting and installation.

Here is an example `config.yaml`:   
```
---
conf:
  tftp_boot_dir: /var/lib/tftpboot
  http_root_dir: /var/www/html
vlan: # One of two below are needed, either VLAN name of VLAN id
  # SAP Cloud
  name: Admin
  #id: 2401459
images:
  - name: SLE12_SP3
    title: SUSE Linux Enterprise Server 12 - SP3
    file_url: http://myserver.com/SLE-12-SP3-Server-DVD-x86_64-GM-DVD1.iso
    md5_url: http://myserver.com/SLE-12-SP3-Server-DVD-x86_64-GM-DVD1.iso.md5    # optional, either md5_url or md5_must be specified
    filename: SLE-12-SP3-Server-DVD-x86_64-GM-DVD1.iso
    save_dir: /root/images
    mount_point: SLE12_SP3                                                        # appended to the value of 'http_root_dir'
  - name: SLE12_SP2
    title: SUSE Linux Enterprise Server 12 - SP2
    file_url: http://myserver.com/SLE-12-SP2-Server-DVD-x86_64-GM-DVD1.iso
    md5_url: http://myserver.com/SLE-12-SP2-Server-DVD-x86_64-GM-DVD1.iso.md5    # optional, either md5_url or md5_must be specified
    filename: SLE-12-SP2-Server-DVD-x86_64-GM-DVD1.iso
    save_dir: /root/images
    mount_point: SLE12_SP2                                                        # appended to the value of 'http_root_dir'

machines:
  - tag: kvm
    image: SLE12_SP3
    yast_template: autoyast_kvmhost.xml     # In the <root_dir>/yast_templates folder
  - tag: compute
    image: SLE12_SP2
    yast_template: autoyast_compute.xml     # In the <root_dir>/yast_templates folder
```

It first specifies the directories for TFTP boot and HTTP files:

```
conf:
  tftp_boot_dir: /var/lib/tftpboot
  http_root_dir: /var/www/html
```

Next, the VLAN info are specified. You can specify either the VLAN name or id.

To specify it by name use something like this:

```
  # SAP Cloud
  name: Admin
```

To specify the VLAN id, using something like this:

```
  # SAP Cloud
  id: 2401459
```

Next, it defines the images section, with the available images. In this example, there are two images, SLES-12-SP2 and SLES-12-SP3:

```
images:
  - name: SLE12_SP3
    title: SUSE Linux Enterprise Server 12 - SP3
    file_url: http://myserver.com/SLE-12-SP3-Server-DVD-x86_64-GM-DVD1.iso
    md5_url: http://myserver.com/SLE-12-SP3-Server-DVD-x86_64-GM-DVD1.iso.md5    # optional, either md5_url or md5_must be specified
    filename: SLE-12-SP3-Server-DVD-x86_64-GM-DVD1.iso
    save_dir: /root/images
    mount_point: SLE12_SP3                                                        # appended to the value of 'http_root_dir'
  - name: SLE12_SP2
    title: SUSE Linux Enterprise Server 12 - SP2
    file_url: http://myserver.com/SLE-12-SP2-Server-DVD-x86_64-GM-DVD1.iso
    md5_url: http://myserver.com/SLE-12-SP2-Server-DVD-x86_64-GM-DVD1.iso.md5    # optional, either md5_url or md5_must be specified
    filename: SLE-12-SP2-Server-DVD-x86_64-GM-DVD1.iso
    save_dir: /root/images
    mount_point: SLE12_SP2                                                        # appended to the value of 'http_root_dir'
```

There are 3 options for MD5 related validation:
- If `md5_url` is specified, the MD5 file is downloaded and the MD5 value in it is used to validate the ISO image
- If `md5_value` is specified, then it should be the MD5 directly in the config file.  This value is used to validate the ISO image
- If neither `md5_url` nor `md5_value` are set, then no MD5 validation is performed on the image, i.e. image always downloaded

The above snippet uses the `md5 file` approach.  To use the `md5 value` approache it would have been written like this:

```
images:
  - name: SLE12_SP3
    title: SUSE Linux Enterprise Server 12 - SP3
    file_url: http://myserver.com/SLE-12-SP3-Server-DVD-x86_64-GM-DVD1.iso
    md5_value: 633537da81d270a9548272dfe1fdd20d                                    # optional, either md5_url or md5_must be specified
    filename: SLE-12-SP3-Server-DVD-x86_64-GM-DVD1.iso
    save_dir: /root/images
    mount_point: SLE12_SP3                                                        # appended to the value of 'http_root_dir'
```

Finally, it defines the "machine" types section, based on SL tags, and how each machine type relates or links to an image to be served and the autoyast template file to use:

```
machines:
  - tag: kvm
    image: SLE12_SP3
    yast_template: autoyast_kvmhost.xml     # In the <root_dir>/yast_templates folder
  - tag: compute
    image: SLE12_SP2
    yast_template: autoyast_compute.xml     # In the <root_dir>/yast_templates folder
```

## Running the scripts

At this point, the config file is created and you are ready to initiate the installation.  In the instructions below, the config file is called `config.yaml`.

1. Transfer the files from this repo along with your `config.yaml` file onto the Boot Server VM
1. Run `setup_boot_server.sh <config_yaml>` - this will perform several tasks:
    - install the required Linux packages
    - install the required python packages
    - setup HTTP server with the minimal configuration
    - setup DHCP server with the minimal/blank configuration
    - setup TFTP server
    - download all the needed ISO images for SUSE
    - mount and make the ISO images available via the HTTP server
    - update the TFTP server's configuration to remote boot machines using the ISO images
1. Run `setup_and_config_host.sh` with the `prepare` verb for each of the type of baremetals (tags) or by hostname to configure DHCP and autoyast files. This can be repeated as many times as necessary. The following are examples:
    - `setup_and_config_host.sh -c <config_yaml> prepare --hostname kvmhost,compute1`
    - `setup_and_config_host.sh -c <config_yaml> prepare --tag kvm,compute`
1. Optionally, run `setup_and_config_host.sh` with the `delete` verb if any hosts configuration needs to be removed. This can be repeated (along with the previous step), as many times as necessary.

    This is an example using hostnames.
    - `setup_and_config_host.sh -c <config_yaml> delete --hostname kvmhost,compute1`
 
    This following is an example using tags. Basically, this will fetch all baremetal machines that have these tags and then use the hostname of each to perform the configuration:
    - `setup_and_config_host.sh -c <config_yaml> delete --tag kvmhost,compute`

    The `all` tag can be used process all tags at once:
    - `setup_and_config_host.sh -c <config_yaml> delete --tag all`

1. Run `setup_and_config_host.sh` with the `apply` verb when all the desired baremetals have been setup using the `prepare` and `delete` verbs. For example:
    - `setup_and_config_host.sh -c <config_yaml> apply`
    
    This will apply the DHCP changes (restart DHCP daemon) and trigger restart of the affected baremetals.  Then it will "wait" to receive notifications from those baremetals being setup.  Once all the notifications have been received, then it stops.

    You may use the `--show` or `--listenOnly` parameters with the `apply` verb.  
    
    The `--show` will simply display what baremetals are going to be rebooted to initiate SUSE OS install.

    The `--listenOnly` will only start the "listener" to wait for notifications from the baremetals being installed.  It can be used basically to "resume" in case of a previous failure in the script.

