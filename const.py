"""Constants for the Home Assistant REST API integration."""

DOMAIN = "ha_rest_api"

# Service constants
SERVICE_GET_LOVELACE_CONFIG = "get_lovelace_config"
SERVICE_SAVE_LOVELACE_CONFIG = "save_lovelace_config"
SERVICE_UPSERT_LOVELACE_VIEW = "upsert_lovelace_view"
SERVICE_DELETE_LOVELACE_VIEW = "delete_lovelace_view"
SERVICE_GET_LOVELACE_SECTION = "get_lovelace_section"
SERVICE_SET_LOVELACE_SECTION = "set_lovelace_section"
SERVICE_RESTART_HASS = "restart_hass"
SERVICE_GET_LOVELACE_LIST = "get_lovelace_list"

# API base paths
API_BASE_PATH = "/api/ha_rest_api"
LOVELACE_API_PATH = f"{API_BASE_PATH}/lovelace"
LOVELACE_SECTION_API_PATH = f"{API_BASE_PATH}/lovelace_section"
LOVELACE_SECTION_DELETE_API_PATH = f"{API_BASE_PATH}/lovelace_section/delete"
LOVELACE_LIST_API_PATH = f"{API_BASE_PATH}/lovelace_list"
RESTART_HASS_API_PATH = f"{API_BASE_PATH}/restart"
