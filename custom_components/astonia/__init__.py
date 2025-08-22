# custom_components/astonia/__init__.py
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_URL, CONF_SCAN_INTERVAL, Platform

from .const import DOMAIN, CONF_CHARACTERS, DEFAULT_SCAN_INTERVAL
from .coordinator import AstoniaCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Astonia from a config entry."""
    url = entry.options.get(CONF_URL, entry.data[CONF_URL])
    scan = entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
    # characters list is read by your platform files when creating entities
    characters = entry.options.get(CONF_CHARACTERS, entry.data.get(CONF_CHARACTERS, []))

    coordinator = AstoniaCoordinator(hass, url, scan)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "characters": characters,
        "url": url,
        "scan": scan,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload entities if options change
    entry.async_on_unload(entry.add_update_listener(_reload_on_update))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _reload_on_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
