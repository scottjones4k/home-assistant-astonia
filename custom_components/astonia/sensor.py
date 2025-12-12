from __future__ import annotations

from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AstoniaCoordinator
from datetime import datetime, timezone


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data: dict[str, Any] = hass.data[DOMAIN][entry.entry_id]
    coordinator: AstoniaCoordinator = data["coordinator"]
    characters: list[str] = data["characters"]

    entities = []
    for char in characters:
        entities.append(AstoniaLevelSensor(coordinator, entry.entry_id, char))
        entities.append(AstoniaClassSensor(coordinator, entry.entry_id, char))
        entities.append(AstoniaLastOnlineSensor(coordinator, entry.entry_id, char))

    async_add_entities(entities)


class _BaseAstoniaSensor(CoordinatorEntity[AstoniaCoordinator], SensorEntity, RestoreEntity):
    """Base sensor which caches last known value when character is offline."""

    _attr_should_poll = False  # coordinator drives updates

    def __init__(self, coordinator: AstoniaCoordinator, entry_id: str, char_name: str) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._char = char_name
        self._key = char_name.lower()
        self._native_value: Optional[Any] = None  # cached value

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self._entry_id}:{self._key}")},
            "name": self._char,
            "manufacturer": "Astonia 3",
            "model": "Who’s Online",
        }

    async def async_added_to_hass(self) -> None:
        """Restore last state on HA restart."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            # Let subclasses parse the restored state
            self._restore_from_state(last_state.state, last_state.attributes)

    def _restore_from_state(self, state: str, attrs: dict[str, Any]) -> None:
        """Subclass hook to restore cached values."""
        # Implemented by subclasses if needed
        return

    def _me(self) -> dict | None:
        players = (self.coordinator.data or {}).get("players", [])
        return next((p for p in players if (p.get("name") or "").lower() == self._key), None)

    def _handle_coordinator_update(self) -> None:
        """Update cached value if online; keep previous value if offline."""
        # Subclasses implement specific field handling
        self._on_snapshot(self._me())
        self.async_write_ha_state()

    def _on_snapshot(self, me: dict | None) -> None:
        """Subclass hook per snapshot."""
        return


class AstoniaLevelSensor(_BaseAstoniaSensor):
    _attr_native_unit_of_measurement = "lvl"

    def __init__(self, coordinator: AstoniaCoordinator, entry_id: str, char_name: str) -> None:
        super().__init__(coordinator, entry_id, char_name)
        self._attr_name = f"{self._char} Level"
        self._attr_unique_id = f"{DOMAIN}:{entry_id}:{self._key}:level"

    @property
    def native_value(self) -> Optional[int]:
        return self._native_value

    def _on_snapshot(self, me: dict | None) -> None:
        # If online & level present, update cache; otherwise keep previous.
        if me is not None:
            lvl = me.get("level")
            if isinstance(lvl, int):
                self._native_value = lvl
            else:
                # Try to coerce numeric strings if your service ever sends them
                try:
                    self._native_value = int(lvl) if lvl is not None else self._native_value
                except Exception:
                    pass

    def _restore_from_state(self, state: str, attrs: dict[str, Any]) -> None:
        try:
            self._native_value = int(state) if state not in (None, "unknown", "unavailable", "") else None
        except Exception:
            self._native_value = None


class AstoniaClassSensor(_BaseAstoniaSensor):
    def __init__(self, coordinator: AstoniaCoordinator, entry_id: str, char_name: str) -> None:
        super().__init__(coordinator, entry_id, char_name)
        self._attr_name = f"{self._char} Class"
        self._attr_unique_id = f"{DOMAIN}:{entry_id}:{self._key}:class"

    @property
    def native_value(self) -> Optional[str]:
        return self._native_value

    def _on_snapshot(self, me: dict | None) -> None:
        if me is not None:
            clz = me.get("clazz")
            if isinstance(clz, str) and clz.strip():
                self._native_value = clz.strip()

    def _restore_from_state(self, state: str, attrs: dict[str, Any]) -> None:
        self._native_value = state if state not in (None, "unknown", "unavailable", "") else None

class AstoniaLastOnlineSensor(_BaseAstoniaSensor):
    def __init__(self, coordinator: AstoniaCoordinator, entry_id: str, char_name: str) -> None:
        super().__init__(coordinator, entry_id, char_name)
        self._attr_name = f"{self._char} Last Online"
        self._attr_unique_id = f"{DOMAIN}:{entry_id}:{self._key}:last_online"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
    @property
    def native_value(self) -> Optional[str]:
        return self._native_value

    def _on_snapshot(self, me: dict | None) -> None:
        if me is not None:
            # Set last_online to current UTC time when player is present
            self._native_value = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _restore_from_state(self, state: str, attrs: dict[str, Any]) -> None:
        self._native_value = state if state not in (None, "unknown", "unavailable", "") else None
