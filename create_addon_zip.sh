#!/bin/bash
# Script to create a proper Kodi addon ZIP file
# Kodi requires files to be in a subdirectory matching the addon ID

ADDON_NAME="plugin.video.rtve"
ZIP_FILE="${ADDON_NAME}.zip"
CURRENT_DIR=$(pwd)

# Remove old ZIP if exists
rm -f "$ZIP_FILE"

# Create a temporary directory for the addon files
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Copy files to temp directory in a subdirectory named after the addon
rsync -av --exclude='*.pyc' \
          --exclude='__pycache__' \
          --exclude='*.pyo' \
          --exclude='.git' \
          --exclude='.idea' \
          --exclude='.venv' \
          --exclude='*.zip' \
          --exclude='create_addon_zip.sh' \
          --exclude='.DS_Store' \
          --exclude='*.swp' \
          --exclude='*.swo' \
          --exclude='*~' \
          --exclude='.kodiignore' \
          . "$TEMP_DIR/$ADDON_NAME/"

# Create ZIP from temp directory with addon folder
cd "$TEMP_DIR"
zip -r "$CURRENT_DIR/$ZIP_FILE" "$ADDON_NAME/" -x "*.pyc" -x "*__pycache__*"

# Change back to original directory
cd "$CURRENT_DIR"

echo "Created $ZIP_FILE"
echo "You can now install this ZIP file in Kodi"

