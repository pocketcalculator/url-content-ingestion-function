#!/usr/bin/env bash
# Copyright (c) Microsoft Corporation.
# SPDX-License-Identifier: MIT
#
# deploy-function.sh
# Deploy infrastructure for the URL content ingestion Azure Function.

set -euo pipefail

usage() {
  echo "Usage: ${0##*/} -s <subscription-id> -g <resource-group> -l <location> -f <function-app-name> [-d <deployment-name>]"
  echo ""
  echo "Required arguments:"
  echo "  -s    Azure subscription ID"
  echo "  -g    Resource group name"
  echo "  -l    Azure location (for example: eastus2)"
  echo "  -f    Function App name (must be globally unique)"
  echo ""
  echo "Optional arguments:"
  echo "  -d    Deployment name (default: function-deploy-<timestamp>)"
  echo "  -h    Show help"
}

err() {
  local message="$1"
  printf "ERROR: %s\n" "${message}" >&2
  exit 1
}

require_command() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    err "'${cmd}' command is required but not installed"
  fi
}

main() {
  local subscription_id=""
  local resource_group=""
  local location=""
  local function_app_name=""
  local deployment_name="function-deploy-$(date +%Y%m%d%H%M%S)"

  while getopts ":s:g:l:f:d:h" opt; do
    case "${opt}" in
      s) subscription_id="${OPTARG}" ;;
      g) resource_group="${OPTARG}" ;;
      l) location="${OPTARG}" ;;
      f) function_app_name="${OPTARG}" ;;
      d) deployment_name="${OPTARG}" ;;
      h)
        usage
        exit 0
        ;;
      :)
        err "Option -${OPTARG} requires an argument"
        ;;
      \?)
        usage
        err "Invalid option: -${OPTARG}"
        ;;
    esac
  done

  if [[ -z "${subscription_id}" || -z "${resource_group}" || -z "${location}" || -z "${function_app_name}" ]]; then
    usage
    err "Missing required arguments"
  fi

  require_command "az"

  az account show >/dev/null
  az account set --subscription "${subscription_id}"

  echo "Ensuring resource group '${resource_group}' exists in '${location}'..."
  az group create \
    --name "${resource_group}" \
    --location "${location}" \
    --output none

  echo "Deploying Bicep template..."
  az deployment group create \
    --name "${deployment_name}" \
    --resource-group "${resource_group}" \
    --template-file "bicep/main.bicep" \
    --parameters \
      functionAppName="${function_app_name}" \
      location="${location}" \
    --query properties.outputs \
    --output json

  echo "Deployment completed successfully."
}

main "$@"
