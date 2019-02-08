#!/bin/bash

if [ $# -eq 0 ]; then
  echo -e "\nERROR: Missing required input param."
  echo -e "\nSYNTAX:$0 <installation_config_yaml> [<generated_config_dir>]"
  echo ""
  exit 1
fi

PYTHON="$(which python)"
[ $? -ne 0 ] && echo "Cannot find python executable. Aborting..." && exit 1

THIS_DIR="$(readlink -f "$(dirname "$0")")"
CONFIG_FILE="$(readlink -f "$1")"

# If generate dir specified, then use it.
if [ $# -gt 1 ]; then
    GEN_DIR="$(readlink -f "$2")"
else
    GEN_DIR="$(readlink -f ./gen)"
fi

#
# Verify the config file exists.
#
echo "Setup config file: ${CONFIG_FILE}"
if [ ! -r "${CONFIG_FILE}" ]; then
    echo "Configuration file \"${CONFIG_FILE}\" either does not exist or is not readable."
    exit 1
fi

#
# If config gen dir does not exist, create it.
#
if [ ! -d "${GEN_DIR}" ]; then
    echo "Creating directory: ${GEN_DIR}"
    mkdir -p "${GEN_DIR}"
    [ $? -ne 0 ] && echo "Error while creating target config generation folder." && exit 1
fi

# Install linux packages
yum install -y httpd dhcp iptables-services mkisofs tftp-server syslinux genisoimage
# Install EPEL repo to install jq
yum install -y epel-release
# Install jq
yum install -y jq

#
# Setup some variables
#
PY_DIR="${THIS_DIR}/py"

#
# Setup python
#
# Update pip first
pip install --upgrade pip
# Install some python modules
pip install -r ${PY_DIR}/requirements.txt
# pip install SoftLayer
# pip install pyyaml
# pip install aenum
# pip install yq

#
# Setup some more variables now that yq is setup.
#
TFTPDIR="$(yq -r '.conf.tftp_boot_dir' "${CONFIG_FILE}")"
[ $? -ne 0 ] && echo "ERROR: Failed to read TFTP boot directory from the config yaml file." && exit 1
HTTPDIR="$(yq -r '.conf.http_root_dir' "${CONFIG_FILE}")"
[ $? -ne 0 ] && echo "ERROR: Failed to read HTTP root directory from the config yaml file." && exit 1

#
# Setup firewall, disable firewalld and use iptables instead.
#
systemctl disable firewalld
systemctl enable iptables
systemctl stop firewalld
iptables -F
iptables -A INPUT -i eth1 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A INPUT -i eth1 -j DROP
iptables-save > /etc/sysconfig/iptables
systemctl start iptables

#
# Setup Apache HTTP Server
#
mkdir -p ${HTTPDIR}/autoyast
echo "Enabling and starting HTTP server"
systemctl enable httpd
systemctl restart httpd

#
# Reset the dhcp
#
cat >/etc/dhcp/dhcpd.conf <<EOF
omapi-port 7911;

shared-network BootServerNet {
    # Subnets to deal with will go here
} # shared network ends here

group {
    # Hosts to deploy OS will go here
}
EOF

#
# Initialize the dhcp conf with the subnet info of the boot server.
#
${PYTHON} ${PY_DIR}/setup_and_config_host.py -c "${CONFIG_FILE}" reset-dhcp

#
# Check if TFTP dir exists.  If not, then create it
#
if [ ! -d "${TFTPDIR}" ]; then
    echo "Creating TFTP directory ${TFTPDIR}..."
    mkdir -p "${TFTPDIR}"
    [ $? -ne 0 ] && echo "Error while creating TFTP top level directory." && exit 1
fi

#
# Create the config files for downloading the SUSE ISO images
#
${PYTHON} ${PY_DIR}/generateConfig.py --genDir "${GEN_DIR}" --config "${CONFIG_FILE}" --scripts download
[ $? -ne 0 ] && echo "Error while generating download scripts" && exit 1

#
# Create the config files for TFTP server config
#
${PYTHON} ${PY_DIR}/generateConfig.py  --genDir "${GEN_DIR}" --config "${CONFIG_FILE}" --scripts tftp
[ $? -ne 0 ] && echo "Error while generating the TFTP config files" && exit 1

#
# Make the generated scripts executable.
#
chmod +x "${GEN_DIR}"/*.sh
[ $? -ne 0 ] && echo "Error while making the generated scripts executable." && exit 1


#
# Process the download images scripts first
#
echo "Calling download scripts."
for file in "${GEN_DIR}"/download_image_*.sh; do
    echo "Executing file: $file"
    $file
    [ $? -ne 0 ] && echo "Error while executing the download script: ${file}.  Aborting..." && exit 1
done


#
# Process the download images scripts first
#
echo "Calling TFTP config scripts."
for file in "${GEN_DIR}"/setup_tftp_for_*.sh; do
    echo "Executing file: $file"
    "$file" "${THIS_DIR}" "${TFTPDIR}"
    [ $? -ne 0 ] && echo -e "Error while executing the TFTP config script. Command line: \n${file} \"${THIS_DIR}"\" "${TFTPDIR}\"\n  Aborting..." && exit 1
done

#
# Enable and start the TFTP server.
#
echo "Enabling and starting TFTP server"
systemctl enable tftp
systemctl restart tftp

#
# Setup the public/private ssh key
#
if [ ! -f /root/.ssh/id_rsa ]; then
    ssh-keygen -q -f /root/.ssh/id_rsa -N ""
    cp /root/.ssh/id_rsa.pub ${HTTPDIR}/
elif [ ! -f ${HTTPDIR}/id_rsa.pub ]; then
    cp /root/.ssh/id_rsa.pub ${HTTPDIR}/
fi
