#!/bin/bash

# Target directory for HA config files on the server
# Defaults to /config (standard for HAOS), but can be overridden as the first argument
HA_CONFIG_DIR=${1:-"/config"}
SSH_HOST="homeassistant"
DOCKER="/usr/local/bin/docker"
LOG_SINCE="12h"

# We will save the files inside the ha-data directory relative to the current workspace
OUT_DIR="$(pwd)/ha-data"
LOGS_DIR="${OUT_DIR}/logs"

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

mkdir -p "${OUT_DIR}" "${LOGS_DIR}"

# --- Config files ---
echo "📁 Fetching config files from ${SSH_HOST}:${HA_CONFIG_DIR}..."

CONFIG_FILES=("automations.yaml" "scenes.yaml" "scripts.yaml" "configuration.yaml")

for file in "${CONFIG_FILES[@]}"; do
    # using cat via SSH instead of scp to bypass missing sftp/scp subsystem
    ssh "${SSH_HOST}" "cat ${HA_CONFIG_DIR}/${file}" > "${OUT_DIR}/${file}" 2>/dev/null
    check_result "${OUT_DIR}/${file}" "${file}"
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
