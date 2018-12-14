#!/bin/bash

WORK_DIR="@image_save_dir@"
IMAGE_MD5="@image_md5_value@"

if [ ! -d "${WORK_DIR}" ]; then
    echo "Target directory for downloading \"${WORK_DIR}\" does not exist. Aborting..."
    exit 1
fi

cd "${WORK_DIR}"
[ $? -ne 0 ] && echo "Failed to switch to download directory \"${WORK_DIR}\". Aborting..." && exit 1

FILE="@image_save_dir@/@image_filename@"
FILE_MD5="${FILE}.md5"

FILE_URL="@image_file_url@"
FILE_MD5_URL="@image_md5_url@"

# If imge MD5 provided, then create the md5 file.
if [ "${IMAGE_MD5}" != "" ]; then
  echo "${IMAGE_MD5} @image_filename@" > "${FILE_MD5}"
else
  rm -f "${FILE_MD5}"
fi

#
# If md5 specified, then download it
#
if [ "$FILE_MD5_URL" != "" ]; then
  rm -f "${FILE_MD5}"
  wget "${FILE_MD5_URL}" -O "${FILE_MD5}"
  [ $? -ne 0 ] && echo "\nERROR while downloading file: ${FILE_MD5_URL}" && exit 2
fi

#
# Now if the file already exists:
#  If it does,  check it against the md5. If valid, then nothing else to do, i.e. set DOWNLOAD_FILE=false
#

DOWNLOAD_FILE="true"

# If we have an md5 and the file already exists, then we check it against the md5 file
#if [ "$FILE_MD5_URL" != "" -a -r "${FILE}" ]; then
if [ -r "${FILE_MD5}" -a -r "${FILE}" ]; then
  echo "File ${FILE} exists.  Checking its md5 from ${FILE_MD5} ..."
  md5sum --status -c "${FILE_MD5}"
  if [ $? -eq 0 ]; then
    DOWNLOAD_FILE="false"
    echo "File exists and MD5 verification successful. Nothing else to do."
  else
    echo "MD5 verification failed. So file will be downloaded again."
    rm -f "${FILE}"
  fi
fi

#
# Now if needed download the file and verify it.
#

if [ "${DOWNLOAD_FILE}" == "true" ]; then
  wget "${FILE_URL}" -O "${FILE}"
  [ $? -ne 0 ] && echo "\nERROR while downloading file: ${FILE_URL}" && exit 2
  if [ -r "${FILE_MD5}" ]; then
    echo "File ${FILE} DOWNLOADED.  Checking its md5 from ${FILE_MD5} ..."
    md5sum --status -c "${FILE_MD5}"
    if [ $? -eq 0 ]; then
      echo "File downloaded and MD5 verification successful. Nothing else to do."
    else
      echo "File downloaded but MD5 verification failed."
      exit 1
    fi
  fi
fi
