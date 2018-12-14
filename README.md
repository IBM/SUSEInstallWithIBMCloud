Create code and processes to automate the deployment of SUSE OpenStack Cloud (SOC) 7 and SUSE Enterprise Storage (SES) 5 on IBM Cloud baremetal systems.
This deployment will provide the Infrastructure-as-a-Service layer for SAP Cloud Platform Private Edition.
Below is a high level explanation of the deployment steps that will be automated:

1 - A IBM Cloud virtual machine will be configured as the boot server to install the baremetal systems with SUSE Linux Enterprise Server (SLES).

2 - The first baremetal system will be SLES12 SP3 and will host KVM VMs that automate the deployment of SOC and SES.

3 - Deploy SLES12 SP3 and SES5 on all of the baremetal systems that will comprise the SES Ceph storage cluster.

4 - Deploy SLES12 SP2 and SOC7 on all of the baremetal systems that will comprise the SOC OpenStack cluster.

5 - Finalize the integration of SOC and SES so that it supports a SAP Cloud Platform Private Edition deployment.

See [initial setup](initial_setup.md) on how the first steps and how to initiate the configuration and setup.