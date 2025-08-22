# custom_components/astonia/coordinator.py
from __future__ import annotations

import logging
from datetime import timedelta

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class AstoniaCoordinator(DataUpdateCoordinator[dict]):
    """Fetch snapshots from your astonia-online service."""

    def __init__(self, hass: HomeAssistant, url: str, scan_interval: int) -> None:
        super().__init__(
            hass,
            _LOGGER,  # <-- use a normal logger
            name="AstoniaCoordinator",
            update_interval=timedelta(seconds=scan_interval),
        )
        self._url = url
        self._session = async_get_clientsession(hass)

    async def _async_update_data(self) -> dict:
        """Fetch and return the latest JSON snapshot."""
        try:
            async with async_timeout.timeout(10):
                resp = await self._session.get(self._url)
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except Exception as err:
            raise UpdateFailed(f"Fetch failed: {err}") from err

        # Minimal sanity check expected shape
        if not isinstance(data, dict) or "players" not in data or not isinstance(data["players"], list):
            raise UpdateFailed("Invalid payload: missing 'players' list")

        return data
