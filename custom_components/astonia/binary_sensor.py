from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AstoniaCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Astonia binary sensors from a config entry."""
    data: dict[str, Any] = hass.data[DOMAIN][entry.entry_id]
    coordinator: AstoniaCoordinator = data["coordinator"]
    characters: list[str] = data["characters"]

    entities: list[AstoniaOnlineBinary] = [
        AstoniaOnlineBinary(coordinator, entry.entry_id, char) for char in characters
    ]
    async_add_entities(entities)


class AstoniaOnlineBinary(CoordinatorEntity[AstoniaCoordinator], BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: AstoniaCoordinator, entry_id: str, char_name: str) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._char = char_name
        key = self._key
        self._attr_name = f"{self._char} Online"
        self._attr_unique_id = f"{DOMAIN}:{entry_id}:{key}:online"

    @property
    def is_on(self) -> bool:
        players = (self.coordinator.data or {}).get("players", [])
        return any((p.get("name") or "").lower() == self._key for p in players)

    @property
    def device_info(self):
        # One HA "device" per character
        return {
            "identifiers": {(DOMAIN, f"{self._entry_id}:{self._key}")},
            "name": self._char,
            "manufacturer": "Astonia 3",
            "model": "Who’s Online",
        }

    @property
    def extra_state_attributes(self):
        # Surface class/level if present in the snapshot
        players = (self.coordinator.data or {}).get("players", [])
        me = next((p for p in players if (p.get("name") or "").lower() == self._key), None)
        if not me:
            return {}
        return {
            "class": me.get("clazz"),
            "level": me.get("level"),
        }

    @property
    def _key(self) -> str:
        return self._char.lower()
