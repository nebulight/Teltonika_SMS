"""Config flow for Teltonika SMS integration."""
from __future__ import annotations

import json as _json
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_MODEM,
    CONF_VERIFY_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _normalise_host(host: str) -> str:
    host = host.strip().rstrip("/")
    if not host.startswith(("http://", "https://")):
        host = f"http://{host}"
    return host


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate credentials by authenticating against the router."""
    host = _normalise_host(data[CONF_HOST])
    ssl = data.get(CONF_VERIFY_SSL, False)

    connector = aiohttp.TCPConnector(ssl=ssl)
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with session.post(
                f"{host}/api/login",
                json={"username": data[CONF_USERNAME], "password": data[CONF_PASSWORD]},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                raw = await resp.text()
                _LOGGER.debug("Teltonika config flow login HTTP %s — %s", resp.status, raw)
                if resp.status == 403:
                    raise InvalidAuth
                if resp.status != 200:
                    raise CannotConnect
                result = _json.loads(raw)
                if not result.get("success"):
                    raise InvalidAuth
        except aiohttp.ClientConnectionError as exc:
            raise CannotConnect from exc
        except (InvalidAuth, CannotConnect):
            raise
        except Exception as exc:
            _LOGGER.exception("Teltonika SMS: Unexpected error during validation")
            raise CannotConnect from exc

    return {"title": f"Teltonika SMS ({host})"}


class TeltonikaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Teltonika SMS."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return TeltonikaOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception during config flow")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(_normalise_host(user_input[CONF_HOST]))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, description={"suggested_value": "192.168.1.1"}): str,
                vol.Required(CONF_USERNAME, default="admin"): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_MODEM, default="1-1"): str,
                vol.Optional(CONF_VERIFY_SSL, default=False): bool,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


class TeltonikaOptionsFlow(config_entries.OptionsFlow):
    """Options flow: test SMS and reconfigure."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["test_sms", "reconfigure"],
        )

    async def async_step_test_sms(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        description_placeholders: dict[str, str] = {}

        if user_input is not None:
            from .services import send_sms
            try:
                await send_sms(
                    self.hass,
                    user_input["test_number"],
                    user_input.get("test_message", "Test from Home Assistant Teltonika SMS"),
                )
                return self.async_create_entry(title="", data={})
            except Exception as exc:
                _LOGGER.error("Teltonika SMS test failed: %s", exc)
                errors["base"] = "test_failed"
                description_placeholders["error"] = str(exc)

        return self.async_show_form(
            step_id="test_sms",
            data_schema=vol.Schema(
                {
                    vol.Required("test_number"): str,
                    vol.Optional(
                        "test_message",
                        default="Test from Home Assistant Teltonika SMS",
                    ): str,
                }
            ),
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        current = self.config_entry.data

        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(self.config_entry, data=user_input)
                return self.async_create_entry(title="", data={})

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current.get(CONF_HOST, "")): str,
                vol.Required(CONF_USERNAME, default=current.get(CONF_USERNAME, "admin")): str,
                vol.Required(CONF_PASSWORD, default=current.get(CONF_PASSWORD, "")): str,
                vol.Required(CONF_MODEM, default=current.get(CONF_MODEM, "1-1")): str,
                vol.Optional(CONF_VERIFY_SSL, default=current.get(CONF_VERIFY_SSL, False)): bool,
            }
        )

        return self.async_show_form(step_id="reconfigure", data_schema=schema, errors=errors)


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""
