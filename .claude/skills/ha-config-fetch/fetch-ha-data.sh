#!/bin/bash
#
# Fetches Home Assistant config snapshots and container logs over SSH into ./ha-data/.
#
# Usage:   fetch-ha-data.sh [HA_CONFIG_DIR]      (default: /config)
# Needs:   a passwordless SSH host alias `homeassistant` in ~/.ssh/config.
# Output:  ha-data/ in the CURRENT directory — run it from your project root.

# Target directory for HA config files on the server
# Defaults to /config (standard for HAOS), but can be overridden as the first argument
HA_CONFIG_DIR=${1:-"/config"}
SSH_HOST="homeassistant"
DOCKER="/usr/local/bin/docker"
LOG_SINCE="12h"
SETUP_GUIDE="https://github.com/calexandre/homeassistant-assistant#-optional-ssh-snapshots"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAX_INCLUDED=500

# Add-on / integration data directories on the server.
# ESPHome device YAMLs live under the ESPHome add-on data dir (derived from HA_CONFIG_DIR).
# Zigbee2MQTT data lives under /share/zigbee2mqtt (absolute; usually root-owned).
ESPHOME_DIR="${HA_CONFIG_DIR}/esphome"
Z2M_DIR="/share/zigbee2mqtt"

# We will save the files inside the ha-data directory relative to the current workspace
OUT_DIR="$(pwd)/ha-data"
LOGS_DIR="${OUT_DIR}/logs"
REGISTRY_OUT="${OUT_DIR}/registry"
ESPHOME_OUT="${OUT_DIR}/esphome"
Z2M_OUT="${OUT_DIR}/zigbee2mqtt"

# Reports download result for a given output file and label; returns 1 on failure
check_result() {
    local file="$1"
    local label="$2"
    if [ -s "${file}" ]; then
        echo "  ✅ ${label}"
        return 0
    fi
    echo "  ⚠️  ${label} (failed or empty)"
    rm "${file}" 2>/dev/null
    return 1
}

echo ""
echo "🏠 Home Assistant Data Fetcher"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Paths and file names end up inside remote shell commands, so only plain ones are allowed.
SAFE_PATH_RE='^/[A-Za-z0-9._/-]*$'
SAFE_NAME_RE='^[A-Za-z0-9._-]+\.yaml$'
SAFE_REL_RE='^[A-Za-z0-9_][A-Za-z0-9._/-]*$'

if [[ ! "${HA_CONFIG_DIR}" =~ ${SAFE_PATH_RE} ]]; then
    echo "❌ Invalid config directory: '${HA_CONFIG_DIR}'"
    echo "   Use a plain absolute path such as /config or /homeassistant."
    exit 2
fi

# --- Preflight: SSH must work without a password prompt ---
if ! ssh -o BatchMode=yes -o ConnectTimeout=10 "${SSH_HOST}" true 2>/dev/null; then
    echo "❌ Cannot reach '${SSH_HOST}' over passwordless SSH."
    echo "   1. Add a 'Host ${SSH_HOST}' entry to ~/.ssh/config pointing at your Home Assistant host."
    echo "   2. Check it works: ssh ${SSH_HOST} ls ${HA_CONFIG_DIR}"
    echo "   Setup guide: ${SETUP_GUIDE}"
    echo ""
    echo "   The MCP features (live entities, docs-backed answers) keep working without SSH."
    exit 1
fi

# Root-owned paths (Zigbee2MQTT data, Docker) need sudo when the SSH user is not root.
# Hosts without sudo (e.g. a root login) read them directly.
REMOTE_SUDO=$(ssh "${SSH_HOST}" 'command -v sudo >/dev/null 2>&1 && echo sudo' 2>/dev/null)

mkdir -p "${OUT_DIR}" "${LOGS_DIR}" "${ESPHOME_OUT}" "${Z2M_OUT}"

# --- Config files ---
echo "📁 Fetching config files from ${SSH_HOST}:${HA_CONFIG_DIR}..."

CONFIG_FILES=("automations.yaml" "scenes.yaml" "scripts.yaml" "configuration.yaml" "customize.yaml")

for file in "${CONFIG_FILES[@]}"; do
    # using cat via SSH instead of scp to bypass missing sftp/scp subsystem
    ssh "${SSH_HOST}" "cat '${HA_CONFIG_DIR}/${file}'" > "${OUT_DIR}/${file}" 2>/dev/null
    check_result "${OUT_DIR}/${file}" "${file}"
done

# The installed version, where /ha-release-notes starts the releases it covers.
ssh "${SSH_HOST}" "cat '${HA_CONFIG_DIR}/.HA_VERSION'" > "${OUT_DIR}/.HA_VERSION" 2>/dev/null
check_result "${OUT_DIR}/.HA_VERSION" ".HA_VERSION"

# --- Files that configuration.yaml includes ---
# Packages and automation, script, and scene folders, fetched into the same layout under ha-data/.
# include_paths.py names each target; every path is checked again here before it reaches ssh.
safe_rel() {
    [[ "$1" =~ ${SAFE_REL_RE} ]] && [[ "$1" != *..* ]] && [[ "$1" != */.* ]] && [[ "$(basename "$1")" != "secrets.yaml" ]]
}

if [ -s "${OUT_DIR}/configuration.yaml" ]; then
    echo ""
    echo "🧩 Fetching files that configuration.yaml includes..."
    if ! command -v python3 >/dev/null 2>&1; then
        echo "  ⏭️  Included files (python3 is needed to read the !include lines)"
    else
        seen=" configuration.yaml ${CONFIG_FILES[*]} "
        queue=("configuration.yaml")
        fetched=0
        # Included files can include more; follow them up to three levels deep.
        for _ in 1 2 3 4; do
            [ "${#queue[@]}" -eq 0 ] && break
            next=()
            for rel in "${queue[@]}"; do
                targets=()
                while IFS= read -r line; do targets+=("$line"); done \
                    < <(python3 -I "${SCRIPT_DIR}/include_paths.py" "${OUT_DIR}" "${rel}" 2>/dev/null)
                for target in "${targets[@]+"${targets[@]}"}"; do
                    kind="${target%% *}"
                    path="${target#* }"
                    safe_rel "${path}" || { echo "  ⏭️  ${path} (skipped: unsafe path)"; continue; }
                    files=()
                    if [ "${kind}" = "dir" ]; then
                        while IFS= read -r line; do files+=("${line#"${HA_CONFIG_DIR}/"}"); done \
                            < <(ssh -n "${SSH_HOST}" "find '${HA_CONFIG_DIR}/${path}' -type f -name '*.yaml'" 2>/dev/null)
                    else
                        files=("${path}")
                    fi
                    for file in "${files[@]+"${files[@]}"}"; do
                        [[ "${seen}" == *" ${file} "* ]] && continue
                        seen="${seen}${file} "
                        safe_rel "${file}" && [[ "${file}" == *.yaml || "${file}" == *.yml ]] \
                            || { echo "  ⏭️  ${file} (skipped: unsafe path)"; continue; }
                        if [ "${fetched}" -ge "${MAX_INCLUDED}" ]; then
                            echo "  ⚠️  Stopped after ${MAX_INCLUDED} included files"
                            break 4
                        fi
                        mkdir -p "$(dirname "${OUT_DIR}/${file}")"
                        ssh -n "${SSH_HOST}" "cat '${HA_CONFIG_DIR}/${file}'" > "${OUT_DIR}/${file}" 2>/dev/null
                        check_result "${OUT_DIR}/${file}" "${file}" && next+=("${file}") && fetched=$((fetched + 1))
                    done
                done
            done
            queue=("${next[@]+"${next[@]}"}")
        done
        [ "${fetched}" -eq 0 ] && echo "  ⏭️  No included files"
    fi
fi

# --- Registries ---
# Areas, devices, entities, and integrations, read from .storage. trim_registry.py trims each one
# in the pipe, so credentials, MAC addresses, and serial numbers never reach the disk.
echo ""
echo "🗂️  Fetching registries from ${SSH_HOST}:${HA_CONFIG_DIR}/.storage..."

if ! command -v python3 >/dev/null 2>&1; then
    echo "  ⏭️  Registries (python3 is needed to trim them)"
else
    mkdir -p "${REGISTRY_OUT}"
    for entry in "core.area_registry:areas" "core.device_registry:devices" "core.entity_registry:entities" "core.config_entries:entries"; do
        store="${entry%%:*}"
        kind="${entry##*:}"
        ssh "${SSH_HOST}" "cat '${HA_CONFIG_DIR}/.storage/${store}'" 2>/dev/null \
            | python3 -I "${SCRIPT_DIR}/trim_registry.py" "${kind}" > "${REGISTRY_OUT}/${kind}.json" 2>/dev/null \
            || rm -f "${REGISTRY_OUT}/${kind}.json"
        check_result "${REGISTRY_OUT}/${kind}.json" "registry/${kind}.json"
    done
fi

# --- ESPHome device YAMLs ---
# Fetch every *.yaml in the ESPHome data dir EXCEPT secrets.yaml (never snapshot secrets).
echo ""
echo "🔌 Fetching ESPHome device YAMLs from ${SSH_HOST}:${ESPHOME_DIR}..."

# List remote yaml basenames; skip if the directory is missing or empty.
REMOTE_ESPHOME_YAMLS=$(ssh "${SSH_HOST}" "ls -1 '${ESPHOME_DIR}'/*.yaml 2>/dev/null" 2>/dev/null | xargs -r -n1 basename)

if [ -z "${REMOTE_ESPHOME_YAMLS}" ]; then
    echo "  ⏭️  ESPHome (no *.yaml files found at ${ESPHOME_DIR})"
else
    for file in ${REMOTE_ESPHOME_YAMLS}; do
        if [ "${file}" = "secrets.yaml" ]; then
            echo "  ⏭️  ${file} (skipped: secrets)"
            continue
        fi
        if [[ ! "${file}" =~ ${SAFE_NAME_RE} ]]; then
            echo "  ⏭️  ${file} (skipped: unsafe file name)"
            continue
        fi
        ssh "${SSH_HOST}" "cat '${ESPHOME_DIR}/${file}'" > "${ESPHOME_OUT}/${file}" 2>/dev/null
        check_result "${ESPHOME_OUT}/${file}" "esphome/${file}"
    done
fi

# --- Zigbee2MQTT data ---
# Fetch configuration.yaml, devices.yaml, groups.yaml, and state.json.
echo ""
echo "🕸️  Fetching Zigbee2MQTT data from ${SSH_HOST}:${Z2M_DIR}..."

if ! ssh "${SSH_HOST}" "${REMOTE_SUDO} test -d ${Z2M_DIR}" 2>/dev/null; then
    echo "  ⏭️  Zigbee2MQTT (no data dir at ${Z2M_DIR})"
else
    Z2M_FILES=("configuration.yaml" "devices.yaml" "groups.yaml" "state.json")

    for file in "${Z2M_FILES[@]}"; do
        ssh "${SSH_HOST}" "${REMOTE_SUDO} cat ${Z2M_DIR}/${file}" > "${Z2M_OUT}/${file}" 2>/dev/null
        check_result "${Z2M_OUT}/${file}" "zigbee2mqtt/${file}"
    done
fi

# --- Container logs ---
# HAOS sends logs to the Systemd Journal (no log file by default), so we read container logs directly
echo ""
echo "📋 Fetching container logs (last ${LOG_SINCE})..."

CONTAINERS=("homeassistant:core.log" "hassio_supervisor:supervisor.log")
LOGS_FAILED=0

for entry in "${CONTAINERS[@]}"; do
    container="${entry%%:*}"
    logfile="${entry##*:}"
    ssh "${SSH_HOST}" "${REMOTE_SUDO} ${DOCKER} logs --since=${LOG_SINCE} ${container} 2>&1" \
        | sed 's/\x1b\[[0-9;]*m//g' > "${LOGS_DIR}/${logfile}"
    check_result "${LOGS_DIR}/${logfile}" "${logfile} (${container})" || LOGS_FAILED=1
done

if [ "${LOGS_FAILED}" -eq 1 ]; then
    echo "  💡 Container logs need Docker access on the host: use the \"Advanced SSH & Web Terminal\""
    echo "     add-on with protection mode turned off. Setup guide: ${SETUP_GUIDE}"
fi

echo ""
echo "🎉 Done! Data saved to ${OUT_DIR}/"
