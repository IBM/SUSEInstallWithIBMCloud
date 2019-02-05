#!/bin/bash

# Steps:
# 1) Check if already mounted.  If so, unmount it.
# 2) create mount dir if it does not exist and make sure it is empty
# 3) Create the output folder structure but first remove any existing files
# 4) Copy files from mounted image
# 5) 

if [ $# -ne 2 ]; then
    echo -e "\nERROR: missing required parameter(s)"
    echo -e "\nSYNTAX: $0 <utils_dir> <TFTP_dir>"
    echo -e "\nwhere:"
    echo -e "\tutils_dir: the directory where the utils are installed, e.g. /root/utils"
    echo -e "\tTFTP_dir: the config dir for TFTP server, e.g. /var/lib/tftpboot"
    echo ""
    exit 1
fi

THIS_DIR="$(dirname $0)"
UTILS_DIR="$1"
BASE_TFTPBOOT="$2"
MOUNT_ISO_CMD="${THIS_DIR}/mount_image.sh"

#
# Verify that the utils dir exists and contains the mount_image.sh file.
#
[ ! -d "${UTILS_DIR}" ] && echo "ERROR: the utils directory \"${UTILS_DIR}\" does not exist." && exit 1
[ ! -x "${MOUNT_ISO_CMD}" ] && echo  "ERROR: mount_iso.sh cannot be found or not executable: ${MOUNT_ISO_CMD}" && exit 1

bootserverIP="@bootserverIP@"

ISO="@image_save_dir@/@image_filename@"
MOUNT_DIR="@http_root_dir@/@image_mount_point@"

IMAGE_TFTPBOOT="${BASE_TFTPBOOT}/bios/x86/@image_name@"
TFTPBOOT_CFG_DIR="${IMAGE_TFTPBOOT}/pxelinux.cfg"

SRC_PXELINUX_CFG="@GEN_DIR@/default_for_@image_name@"
SRC_PXELINUX_BOOT_MSG="@GEN_DIR@/boot_msg_for_@image_name@"

PXELINUX_0="/usr/share/syslinux/pxelinux.0"
BOOT_INITRD="${MOUNT_DIR}/boot/x86_64/loader/initrd"
BOOT_LINUX="${MOUNT_DIR}/boot/x86_64/loader/linux"

#
# Attempt to mount the image
#
${MOUNT_ISO_CMD} "${ISO}" "${MOUNT_DIR}"
[ $? -ne 0 ] && echo "ERROR while mounting the ISO image for @image_name@: ${ISO}. Aborting..." && exit 1

echo "Target TFTP boot directory for image @image_name@: ${IMAGE_TFTPBOOT}"

# Remove any previous files
if [ -d "${IMAGE_TFTPBOOT}" ]; then
    echo "Removing any previous files from: ${IMAGE_TFTPBOOT}"
    rm -fR "${IMAGE_TFTPBOOT}"
    [ $? -ne 0 ] && echo "ERROR: Failed to delete directory ${IMAGE_TFTPBOOT} before starting. Aborting..." && exit 1
fi

# Create target directories. Creating the deepest one will also create the parent TFTP boot directory for the image.
echo "Creating PXE boot cfg directory and files: ${TFTPBOOT_CFG_DIR}"
mkdir -p "${TFTPBOOT_CFG_DIR}"
[ $? -ne 0 ] && echo "ERROR: Failed to create directory ${TFTPBOOT_CFG_DIR}. Aborting..." && exit 1

# Copy the boot msg and default config
cp "${SRC_PXELINUX_CFG}" "${TFTPBOOT_CFG_DIR}/default"
[ $? -ne 0 ] && echo "ERROR: Failed to copy file \"${src}\" to \"${dest}\". Aborting..." && exit 1
cp "${SRC_PXELINUX_BOOT_MSG}" "${TFTPBOOT_CFG_DIR}/boot.msg"
[ $? -ne 0 ] && echo "ERROR: Failed to copy file \"${src}\" to \"${dest}\". Aborting..." && exit 1

#
# Copy the linux and initrd boot loader files from the image
#
cp "${BOOT_INITRD}"  "${IMAGE_TFTPBOOT}"
[ $? -ne 0 ] && echo "ERROR: Failed to copy file \"${BOOT_INITRD}\" to \"${IMAGE_TFTPBOOT}\". Aborting..." && exit 1
cp "${BOOT_LINUX}"  "${IMAGE_TFTPBOOT}"
[ $? -ne 0 ] && echo "ERROR: Failed to copy file \"${BOOT_LINUX}\" to \"${IMAGE_TFTPBOOT}\". Aborting..." && exit 1

#
# Finally, copy the pxelinux.0 file to the files for the image
#
cp "${PXELINUX_0}" "${IMAGE_TFTPBOOT}"
[ $? -ne 0 ] && echo "ERROR: Failed to copy file \"${PXELINUX_0}\" to \"${IMAGE_TFTPBOOT}\". Aborting..." && exit 1

exit 0