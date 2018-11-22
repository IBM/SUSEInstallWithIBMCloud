**The README.md lists 5 high level deployment steps. This document is not intended to provide each and every step to manually deploy SUSE OpenStack Cloud and SUSE Enterprise Storage. Rather this document provides details for developing automation to deploy SOC and SES.  Use this document as a reference while reviewing the automation.**

### 1. Prepare bootvm to for AutoYAST installs of baremetal systems
The bootvm is a CentOS7 IBM Cloud virtual server with the following configuration.
  * Additional packges installed:
    * dhcp
    * tftp-server
    * httpd
  * Configure dhcp
    * Serve IP address and PXEboot details by MAC address
  * Configure tftp-server
    * Serve SLES installer for standard and EFI bios by IP address
    * Provide links to httpd hosted install media and AutoYAST file
    * Allow tftp puts to set boot from local disk after AutoYAST install completion by IP address
    * Default to boot from local disk if there is an unknown IP address
  * Configure http
    * Serve SLES12 SP2 and SLES12 SP3 install media
    * Serve AutoYAST files for
      * kvmhost
      * soc control and compute nodes
      * ses nodes

### 2. Install kvmhost via AutoYAST file with post-install script
  * Install SLES 12 SP3 for kvmhost
  * Customized AutoYAST includes:
    * hostname
    * ntp configuration
    * Register with SUSE
    * Patterns
      * Minimal
      * base
      * kvm_server
      * kvm_tools
      * smt
      * x11
    * Packages
      * lio-utils
    * Runlevel 3
    * Basic IP address configuration

        ---
        ##### Checkpoint/Restart
        ---

  * /etc/init.d/after.local post-install script
    - Test and report issues with bonds, vlans and IP addresses
      * Copy preconfigured files for bond0 and bond1
      * Copy preconfigured files for network bridges for KVM
      * Copy preconfigured files for IP addresses
        - Admin, Public API, Storage Replication (bond0) vlans
        - Storage client (bond1) vlan
    - Setup SMT server
      - Enable repos to be mirrored
      - Mirror repos
    - NFS export /srv/www/htdocs/repo
    - Create raw disk file and iscsi target for soc pacemaker
    - Enable KVM
    - Copy soc-admin and ses-admin qcow2 disk images
      * **TBD - WHAT IS INCLUDED IN THE DISK IMAGES**
    - Mount soc-admin disk image and copy preconfigured files or edit
      * /etc/sysconfig/network files
      * /etc/crowbar/network.json
      * /etc/fstab - edit to add nfs mount of smt repo
        - mount -a
      * /root/crowbar-batch.yaml
      * /etc/init.d/after.local - to be started at initial boot to finalize admin server installation
          1. Register with SMT
          - Apply all available patches
          - Reboot
          - Verify items before install-suse-cloud
              - hostname -f
              - ntpq -p
              - Required software repos
          - Complete soc-admin server installation
            1. systemctl start crowbar-init
            - crowbarctl database create
            - screen install-suse-cloud -v
    - Mount ses-admin disk image and copy preconfigured files or edit
      * /etc/sysconfig/network files
      * /etc/hosts - with all SES node hostnames
      * /etc/init.d/after.local - to be started at initial boot to finalize admin server installation
          1. Register with SMT
          2. Apply all available patches
          3. Reboot
          4. Verify items before starting salt
              * ntpq -p
          - Enable and start salt-master
          - Edit /etc/salt/minion.d/master.conf
            ```
          master: <hostname of master>
            ```
          - Enable and start salt-minion
          - Gather local salt fingerprint
          - Record for salt-master to review

            ---
            ##### Checkpoint/Restart
            ---
    - Start soc-admin and ses-admin VMs
    - Verify crowbar is ready
    - Verify salt-master is ready

---
##### Checkpoint/Restart
---

### 3.0. Install ses- nodes via AutoYAST file with post-install script
  * Install SLES 12 SP3 for all ses- nodes
  * Customized AutoYAST includes
    - hostname
    - ntp configuration
    - Register with SMT
    - Patterns
      - Minimal
      - base
    - Packages
      - salt-minion
    - Configuration for bond0 and bond1
    - IP address configuration
      - bond0
        - For ses-osd*, Admin, Storage Replication vlans
        - For ses-mon*, Admin vlan
        - For ses-swift*, Admin, Public API vlans
      - bond1
        - For ses-*, Storage client (bond1) vlan

            ---
            ##### Checkpoint/Restart
            ---

  * /etc/init.d/after.local post-install script
    1. Test and report issues with bonds, vlans and IP addresses
    2. Local “/etc/hosts” with all SES node hostnames
    3. Edit /etc/salt/minion.d/master.conf
        ```
        master: <hostname of master>
        ```
    4. Enable and start salt-minion
    - Gather local salt fingerprint
    - Record for salt-master to review
    - **SHOULD SSD DRIVES FOR OSDS BE WIPED???**

---
##### Checkpoint/Restart
---

### 3.1. Continue SES deployment on ses-admin
  1. Review all gathered salt minion fingerprints with salt-key -F
    - salt-key --accept-all
  - zypper in deapsea
  - **TARGET WITH DEEPSEA_MINIONS OPTION???**
  - Edit /srv/pillar/ceph/master_minion.sls
```
    master_minion: <hostname of master>
```
  - salt-run state.orch ceph.stage.prep
  - **salt-run state.orch ceph.migrate.subvolume???  (if btrfs filesystem is deployed)**
  - salt-run state.orch ceph.stage.discovery
  - Edit /srv/pillar/ceph/stack/ceph/cluster.yml
    - cluster_network: and public_network:
  - Copy preconfigured /srv/pillar/ceph/proposals/policy.cfg file
  - salt-run state.orch ceph.stage.configure
    1. Verify pillar configuration data
  - salt-run state.orch ceph.stage.deploy
  - Verify cluster status
    1. ceph -s
  - salt-run state.orch ceph.stage.services
  - Verify cluster health
    1. ceph health - **May need to increase pg_num AND pgp_num TO 32 OR 64 for radosgw pools**
  - Create rbd pool with 32 or 64 pg_num and pgp_num
  - Create rbd images
    - soc-ha-sbd2
    - soc-ha-sbd3

---
##### Checkpoint/Restart
---

### 4.0. Install 4 - 6 soc- nodes at one time via AutoYAST file with post-install script
**NOTE:** Due to number of available IP addresses in admin dhcp range
  * Install SLES 12 SP2 for all soc- nodes
  * Customized AutoYAST includes
    - hostname
    - DHCP configuration for eth0
    - Patterns
      - Minimal
      - base
    - Packages
      - ceph-common

        ---
        ##### Checkpoint/Restart
        ---

  - /etc/init.d/after.local post-install script
    1. Test and report issues with bonds, vlans and IP addresses
    2. wget -O crowbar_register http://<soc admin network IP>:8091/suse-12.2/x86_64/crowbar_register
    3. crowbar_register –keep-existing-hostname
    4. Copy /etc/ceph/ceph.conf and /etc/ceph/ceph.client.admin.keyring from ses-admin
    5. Copy ssl certificates to /etc/crowbar/ssl/certs and /etc/crowbar/ssl/private
      * With following directory ownership and permissions

          ```
          ssl:
          drwxr-xr-x root root certs
          drwxr-xr-x root root private

          ssl/certs:
          -rw-r--r-- root root DigiCertCA.crt
          -rw-r--r-- root root sapcp.cloud.ibm.com.crt

          ssl/private:
          -rw-r--r-- root root sapcp.cloud.ibm.com.key
          ```
    6. For soc-control* nodes, add sbd devices
      1. Attach and make persistent iscsi target
      2. Attach and make persistent rbd devices
    7. zypper patch
    8. reboot

---
##### Checkpoint/Restart
---

### 4.1. Continue SOC deployment on soc-admin
  1. Execute crowbar batch
    - Adjust crowbar batch yaml based on SAP SCP PE Infrastructure guidelines before executing crowbar batch

### 5. Finalize the integration of SOC and SES
  1. Complete additional configuration of based details in the SAP SCP PE Infrastructure guide
