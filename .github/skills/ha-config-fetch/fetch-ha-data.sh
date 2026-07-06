#!/bin/bash

# Target directory for HA config files on the server
# Defaults to /config (standard for HAOS), but can be overridden as the first argument
HA_CONFIG_DIR=${1:-"/config"}
SSH_HOST="homeassistant"
DOCKER="/usr/local/bin/docker"
LOG_SINCE="12h"

# Add-on / integration data directories on the server.
# ESPHome device YAMLs live under the ESPHome add-on data dir (derived from HA_CONFIG_DIR).
# Zigbee2MQTT data lives under /share/zigbee2mqtt (absolute; requires sudo to read).
ESPHOME_DIR="${HA_CONFIG_DIR}/esphome"
Z2M_DIR="/share/zigbee2mqtt"

# We will save the files inside the ha-data directory relative to the current workspace
OUT_DIR="$(pwd)/ha-data"
LOGS_DIR="${OUT_DIR}/logs"
ESPHOME_OUT="${OUT_DIR}/esphome"
Z2M_OUT="${OUT_DIR}/zigbee2mqtt"

# Reports download result for a given output file and label
check_result() {
    local file="$1"
    local label="$2"
    if [ -s "${file}" ]; then
        echo "  ✅ ${label}"
    else
        echo "  ⚠️  ${label} (failed or empty)"
        rm "${file}" 2>/dev/null
    fi
}

echo ""
echo "🏠 Home Assistant Data Fetcher"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

mkdir -p "${OUT_DIR}" "${LOGS_DIR}" "${ESPHOME_OUT}" "${Z2M_OUT}"

# --- Config files ---
echo "📁 Fetching config files from ${SSH_HOST}:${HA_CONFIG_DIR}..."

CONFIG_FILES=("automations.yaml" "scenes.yaml" "scripts.yaml" "configuration.yaml" "customize.yaml")

for file in "${CONFIG_FILES[@]}"; do
    # using cat via SSH instead of scp to bypass missing sftp/scp subsystem
    ssh "${SSH_HOST}" "cat ${HA_CONFIG_DIR}/${file}" > "${OUT_DIR}/${file}" 2>/dev/null
    check_result "${OUT_DIR}/${file}" "${file}"
done

# --- ESPHome device YAMLs ---
# Fetch every *.yaml in the ESPHome data dir EXCEPT secrets.yaml (never snapshot secrets).
echo ""
echo "🔌 Fetching ESPHome device YAMLs from ${SSH_HOST}:${ESPHOME_DIR}..."

# List remote yaml basenames; skip if the directory is missing or empty.
REMOTE_ESPHOME_YAMLS=$(ssh "${SSH_HOST}" "ls -1 ${ESPHOME_DIR}/*.yaml 2>/dev/null" 2>/dev/null | xargs -r -n1 basename)

if [ -z "${REMOTE_ESPHOME_YAMLS}" ]; then
    echo "  ⚠️  ESPHome (no *.yaml files found at ${ESPHOME_DIR})"
else
    for file in ${REMOTE_ESPHOME_YAMLS}; do
        if [ "${file}" = "secrets.yaml" ]; then
            echo "  ⏭️  ${file} (skipped: secrets)"
            continue
        fi
        ssh "${SSH_HOST}" "cat ${ESPHOME_DIR}/${file}" > "${ESPHOME_OUT}/${file}" 2>/dev/null
        check_result "${ESPHOME_OUT}/${file}" "esphome/${file}"
    done
fi

# --- Zigbee2MQTT data ---
# Fetch configuration.yaml, devices.yaml, groups.yaml, and state.json.
# The Z2M data dir is owned by root, so we read via sudo.
echo ""
echo "🕸️  Fetching Zigbee2MQTT data from ${SSH_HOST}:${Z2M_DIR}..."

Z2M_FILES=("configuration.yaml" "devices.yaml" "groups.yaml" "state.json")

for file in "${Z2M_FILES[@]}"; do
    ssh "${SSH_HOST}" "sudo cat ${Z2M_DIR}/${file}" > "${Z2M_OUT}/${file}" 2>/dev/null
    check_result "${Z2M_OUT}/${file}" "zigbee2mqtt/${file}"
done

# --- Container logs ---
# HAOS sends logs to the Systemd Journal (no log file by default), so we read container logs directly
echo ""
echo "📋 Fetching container logs (last ${LOG_SINCE})..."

CONTAINERS=("homeassistant:core.log" "hassio_supervisor:supervisor.log")

for entry in "${CONTAINERS[@]}"; do
    container="${entry%%:*}"
    logfile="${entry##*:}"
    ssh "${SSH_HOST}" "sudo ${DOCKER} logs --since=${LOG_SINCE} ${container} 2>&1" \
        | sed 's/\x1b\[[0-9;]*m//g' > "${LOGS_DIR}/${logfile}"
    check_result "${LOGS_DIR}/${logfile}" "${logfile} (${container})"
done

echo ""
echo "🎉 Done! Data saved to ${OUT_DIR}/"
