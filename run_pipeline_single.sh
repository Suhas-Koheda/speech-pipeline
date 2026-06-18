#!/bin/bash

# Default target link
TARGET_LINK="https://www.youtube.com/watch?v=mFE75g9W--Q"

# Check if a different link was passed as an argument
if [ -n "$1" ]; then
    TARGET_LINK="$1"
fi

echo "=== Running pipeline for single link: $TARGET_LINK ==="

# Backup existing links.txt if it exists
if [ -f "links.txt" ]; then
    echo "Backing up links.txt to links.txt.bak"
    cp links.txt links.txt.bak
fi

# Write only the target link to links.txt
echo "$TARGET_LINK" > links.txt

# Run the pipeline orchestrator end-to-end using python3
python3 main.py

# Restore links.txt from backup
if [ -f "links.txt.bak" ]; then
    echo "Restoring links.txt from backup"
    mv links.txt.bak links.txt
fi

echo "=== Pipeline run complete for single link. ==="
