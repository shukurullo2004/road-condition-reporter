#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Define variables
API_KEY="YOUR_API_KEY"  # Replace with your actual Roboflow API key
WORKSPACE="gemas-sudyz"
PROJECT="gemastik-4y25i"
VERSION="5"
DESTINATION_FORMAT="yolov8"

# Temporary Python script for dataset download
PYTHON_SCRIPT="download_dataset.py"

# Check if Python is installed
if ! command -v python &> /dev/null
then
    echo "Python is not installed. Please install Python before running this script."
    exit 1
fi

# Check if roboflow is installed, and install it if necessary
if ! python -c "import roboflow" &> /dev/null
then
    echo "Roboflow library not found, installing it..."
    pip install roboflow
fi

# Create the Python script for downloading the dataset
cat <<EOF > ${PYTHON_SCRIPT}
from roboflow import Roboflow
rf = Roboflow(api_key="${API_KEY}")
project = rf.workspace("${WORKSPACE}").project("${PROJECT}")
version = project.version(${VERSION})
version.download("${DESTINATION_FORMAT}")
EOF

echo "Downloading the dataset..."
python ${PYTHON_SCRIPT}

# Clean up temporary Python script
echo "Cleaning up..."
rm -f ${PYTHON_SCRIPT}

echo "Dataset downloaded successfully!"
