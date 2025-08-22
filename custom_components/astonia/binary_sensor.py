from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

class AstoniaOnline(CoordinatorEntity, BinarySensorEntity):
    _attr_device_class = "connectivity"

    def __init__(self, coordinator, char):
        super().__init__(coordinator)
        self.char = char
        self._attr_name = f"{char} Online"
        self._attr_unique_id = f"{DOMAIN}_{char.lower()}_online"

    @property
    def is_on(self):
        players = self.coordinator.data.get("players", [])
        return any(p["name"].lower() == self.char.lower() for p in players)
