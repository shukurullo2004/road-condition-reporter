#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Google Drive file ID and file name
FILE_ID="1RSJbLJsbXpwF2LpABALPuRK5kbnTuVbp"
FILE_NAME="best.pt"

# Destination folder
WEIGHTS_DIR="models/weights"

# Temporary download file name
TEMP_FILE="temp_model.zip"

echo "Downloading model from Google Drive..."
# Use gdown to download the file (ensure gdown is installed)
if ! command -v gdown &> /dev/null
then
    echo "gdown not found, installing it..."
    pip install gdown
fi

gdown "https://drive.google.com/uc?id=${FILE_ID}" -O ${FILE_NAME}

echo "Download complete."

# Create weights directory if it doesn't exist
if [ ! -d "${WEIGHTS_DIR}" ]; then
    echo "Creating directory: ${WEIGHTS_DIR}"
    mkdir -p "${WEIGHTS_DIR}"
fi

# Move the downloaded file to the weights directory
echo "Moving ${FILE_NAME} to ${WEIGHTS_DIR}"
mv ${FILE_NAME} "${WEIGHTS_DIR}/${FILE_NAME}"

echo "Model moved to ${WEIGHTS_DIR}/${FILE_NAME}"

# Clean up
echo "Cleaning up temporary files..."
rm -f ${TEMP_FILE}

echo "Done."
