from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AstoniaCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Astonia sensors from a config entry."""
    data: dict[str, Any] = hass.data[DOMAIN][entry.entry_id]
    coordinator: AstoniaCoordinator = data["coordinator"]
    characters: list[str] = data["characters"]

    entities = []
    for char in characters:
        entities.append(AstoniaLevelSensor(coordinator, entry.entry_id, char))
        entities.append(AstoniaClassSensor(coordinator, entry.entry_id, char))

    async_add_entities(entities)


class _BaseAstoniaSensor(CoordinatorEntity[AstoniaCoordinator], SensorEntity):
    """Shared helpers for class/level sensors."""

    def __init__(self, coordinator: AstoniaCoordinator, entry_id: str, char_name: str) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._char = char_name

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self._entry_id}:{self._key}")},
            "name": self._char,
            "manufacturer": "Astonia 3",
            "model": "Who’s Online",
        }

    def _me(self) -> dict | None:
        players = (self.coordinator.data or {}).get("players", [])
        return next((p for p in players if (p.get("name") or "").lower() == self._key), None)

    @property
    def _key(self) -> str:
        return self._char.lower()


class AstoniaLevelSensor(_BaseAstoniaSensor):
    _attr_native_unit_of_measurement = "lvl"

    def __init__(self, coordinator: AstoniaCoordinator, entry_id: str, char_name: str) -> None:
        super().__init__(coordinator, entry_id, char_name)
        self._attr_name = f"{self._char} Level"
        self._attr_unique_id = f"{DOMAIN}:{entry_id}:{self._key}:level"

    @property
    def native_value(self):
        me = self._me()
        return me.get("level") if me else None

    @property
    def extra_state_attributes(self):
        me = self._me()
        return {"class": me.get("clazz")} if me else {}


class AstoniaClassSensor(_BaseAstoniaSensor):
    def __init__(self, coordinator: AstoniaCoordinator, entry_id: str, char_name: str) -> None:
        super().__init__(coordinator, entry_id, char_name)
        self._attr_name = f"{self._char} Class"
        self._attr_unique_id = f"{DOMAIN}:{entry_id}:{self._key}:class"

    @property
    def native_value(self):
        me = self._me()
        return me.get("clazz") if me else None
