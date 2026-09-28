#!/usr/bin/env bash
set -e

# Configuration
RELEASE_TAG="v1.0.1"
REPO="fahares/fahares-corpus"
ARCHIVE_NAME="fahares_json_${RELEASE_TAG}.tar.gz"
DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${RELEASE_TAG}/${ARCHIVE_NAME}"

# Locate repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
JSON_DIR="${REPO_ROOT}/json"

echo "=================================================================="
echo "Downloading Fahares JSON Dataset (${RELEASE_TAG}) to ${JSON_DIR}"
echo "=================================================================="

mkdir -p "${JSON_DIR}"
TEMP_ARCHIVE="${REPO_ROOT}/${ARCHIVE_NAME}"

if command -v curl &> /dev/null; then
    echo "Downloading via curl from: ${DOWNLOAD_URL}"
    curl -L --fail --progress-bar "${DOWNLOAD_URL}" -o "${TEMP_ARCHIVE}"
elif command -v wget &> /dev/null; then
    echo "Downloading via wget from: ${DOWNLOAD_URL}"
    wget -q --show-progress "${DOWNLOAD_URL}" -O "${TEMP_ARCHIVE}"
else
    echo "Error: Neither curl nor wget was found on your system."
    exit 1
fi

echo "Extracting archive to ${JSON_DIR}..."
tar -xzf "${TEMP_ARCHIVE}" -C "${JSON_DIR}"
rm -f "${TEMP_ARCHIVE}"

echo "=================================================================="
echo "Successfully downloaded and extracted all 34 volumes to:"
echo "${JSON_DIR}"
echo "=================================================================="
