"""Home Assistant REST API integration."""
import logging
from typing import Dict

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .api.lovelace import async_setup_lovelace_api
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({})}, 
    extra=vol.ALLOW_EXTRA
)

async def async_setup(hass: HomeAssistant, config: Dict) -> bool:
    """Set up the Home Assistant REST API component."""
    # Initialize API endpoints
    await async_setup_lovelace_api(hass)
    
    _LOGGER.info("Home Assistant REST API initialized")
    return True
