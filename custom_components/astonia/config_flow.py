# custom_components/astonia/config_flow.py
from __future__ import annotations

from typing import Any, Dict, List

import aiohttp
import asyncio
import async_timeout
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_URL, CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_CHARACTERS, DEFAULT_SCAN_INTERVAL


# ---- helpers ----------------------------------------------------------------


async def _validate_input(
    hass: HomeAssistant, url: str
) -> Dict[str, Any]:
    """Validate that the service is reachable and returns the expected JSON."""
    try:
        async with aiohttp.ClientSession() as session:
            with async_timeout.timeout(10):
                async with session.get(url) as resp:
                    if resp.status != 200:
                        raise CannotConnect(f"HTTP {resp.status}")
                    data = await resp.json(content_type=None)
    except asyncio.TimeoutError as err:  # type: ignore[name-defined]
        raise CannotConnect("timeout") from err
    except aiohttp.ClientError as err:
        raise CannotConnect("client_error") from err
    except Exception as err:  # JSON decode, etc.
        raise InvalidResponse("bad_json") from err

    if not isinstance(data, dict) or "players" not in data or not isinstance(data["players"], list):
        raise InvalidResponse("missing_players")

    # Minimal sanity: each player should have a "name"
    for p in data["players"]:
        if not isinstance(p, dict) or "name" not in p:
            raise InvalidResponse("player_missing_name")

    # If all good, return a normalized title
    return {
        "title": "Astonia Online",
    }


def _split_chars(raw: str | List[str]) -> List[str]:
    if isinstance(raw, list):
        return [c.strip() for c in raw if c and c.strip()]
    return [c.strip() for c in raw.split(",") if c.strip()]


# ---- exceptions --------------------------------------------------------------


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidResponse(Exception):
    """Error to indicate unexpected payload."""


# ---- Config Flow -------------------------------------------------------------


class AstoniaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Astonia 3."""

    VERSION = 1

    async def async_step_user(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        errors: Dict[str, str] = {}

        if user_input is not None:
            url = user_input[CONF_URL].strip()
            characters = _split_chars(user_input[CONF_CHARACTERS])
            scan = int(user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

            # Prevent duplicates by URL
            await self.async_set_unique_id(url)
            self._abort_if_unique_id_configured()

            # Validate the endpoint
            try:
                info = await _validate_input(self.hass, url)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidResponse:
                errors["base"] = "invalid_response"
            except Exception:  # pragma: no cover
                errors["base"] = "unknown"

            if not errors:
                return self.async_create_entry(
                    title=info.get("title", "Astonia Online"),
                    data={
                        CONF_URL: url,
                        CONF_SCAN_INTERVAL: scan,
                        CONF_CHARACTERS: characters,
                    },
                )

        # Initial form (or re-show with errors)
        data_schema = vol.Schema(
            {
                vol.Required(CONF_URL, default="http://localhost:8000/online.json"): str,
                vol.Required(CONF_CHARACTERS, default=""): str,  # comma-separated
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def async_step_import(self, user_input: Dict[str, Any]) -> FlowResult:
        """Handle import from YAML if ever added (optional)."""
        # Not supporting YAML import; just route to user step.
        return await self.async_step_user(user_input)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return AstoniaOptionsFlow(config_entry)


# ---- Options Flow ------------------------------------------------------------


class AstoniaOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Astonia 3."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        errors: Dict[str, str] = {}

        data = {**self.config_entry.data, **self.config_entry.options}
        url = data.get(CONF_URL, "http://localhost:8000/online.json")
        chars_current = data.get(CONF_CHARACTERS, [])
        chars_default = ",".join(chars_current) if isinstance(chars_current, list) else str(chars_current)
        scan_default = int(data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

        if user_input is not None:
            new_url = user_input[CONF_URL].strip()
            new_chars = _split_chars(user_input[CONF_CHARACTERS])
            new_scan = int(user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

            # Validate (only if URL changed or on every save — here: always validate)
            try:
                await _validate_input(self.hass, new_url)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidResponse:
                errors["base"] = "invalid_response"
            except Exception:
                errors["base"] = "unknown"

            if not errors:
                # Persist changes into options (not data) so you can edit later
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_URL: new_url,
                        CONF_SCAN_INTERVAL: new_scan,
                        CONF_CHARACTERS: new_chars,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_URL, default=url): str,
                vol.Required(CONF_CHARACTERS, default=chars_default): str,
                vol.Optional(CONF_SCAN_INTERVAL, default=scan_default): int,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
