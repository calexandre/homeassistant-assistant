#!/bin/bash

# Target directory for HA config files on the server
# Defaults to /config (standard for HAOS), but can be overridden as the first argument
HA_CONFIG_DIR=${1:-"/config"}
SSH_HOST="homeassistant"

# We will save the files inside the ha-configs directory relative to the current workspace
OUT_DIR="$(pwd)/ha-configs"

echo "Creating output directory ${OUT_DIR}..."
mkdir -p "${OUT_DIR}"

echo "Fetching Home Assistant configuration files from ${SSH_HOST}:${HA_CONFIG_DIR}..."

FILES=("automations.yaml" "scenes.yaml" "scripts.yaml" "configuration.yaml")

for file in "${FILES[@]}"; do
    echo "Fetching $file..."
    # using cat via SSH instead of scp to bypass missing sftp/scp subsystem
    ssh "${SSH_HOST}" "cat ${HA_CONFIG_DIR}/${file}" > "${OUT_DIR}/${file}" 2>/dev/null

    if [ -s "${OUT_DIR}/${file}" ]; then
        echo "Successfully downloaded $file"
    else
        echo "Warning: Failed to download $file or file is empty."
        rm "${OUT_DIR}/${file}" 2>/dev/null
    fi
done

echo "Done. Config files have been fetched to the ${OUT_DIR}/ folder."
