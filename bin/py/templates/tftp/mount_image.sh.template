#!/bin/bash

if [ $# -ne 2 ]; then
  echo -e "\nERROR: Missing required input params."
  echo -e "\nSYNTAX:$0 <image_to_mount> <mount_point>"
  echo ""
  exit 1
fi

ISO="$1"
MNT="$2"

# Verify the ISO image exists.
if [ ! -f "$ISO" ]; then
  echo -e "\nERROR: ISO image does not exist or is not readable: $ISO"
  exit 2
fi

# # Fail if something goes wrong.
# set -e

# Check if the mount point exists.  If not, create it.
if [ ! -d "$MNT" ]; then
  mkdir -p "$MNT"
fi

# Check if mounted.  If not mounted, then mount it.
mount | grep " ${MNT} " | grep -q ${ISO}
if [ $? -ne 0 ]; then
  mount -o loop ${ISO} ${MNT}
fi
