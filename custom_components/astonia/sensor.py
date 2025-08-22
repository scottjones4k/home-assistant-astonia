from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

class AstoniaLevel(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, char):
        super().__init__(coordinator)
        self.char = char
        self._attr_name = f"{char} Level"
        self._attr_unique_id = f"astonia_{char.lower()}_level"
        self._attr_unit_of_measurement = "lvl"

    @property
    def native_value(self):
        players = self.coordinator.data.get("players", [])
        for p in players:
            if p["name"].lower() == self.char.lower():
                return p.get("level")
        return None
