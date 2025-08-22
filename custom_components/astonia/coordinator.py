from datetime import timedelta
import aiohttp
import async_timeout
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from .const import DOMAIN

class AstoniaCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, url: str, scan_interval: int):
        super().__init__(
            hass,
            hass.helpers.logger.logger.getChild(DOMAIN),
            name="AstoniaCoordinator",
            update_interval=timedelta(seconds=scan_interval),
        )
        self._url = url

    async def _async_update_data(self):
        async with aiohttp.ClientSession() as session:
            with async_timeout.timeout(10):
                async with session.get(self._url) as resp:
                    resp.raise_for_status()
                    return await resp.json()
