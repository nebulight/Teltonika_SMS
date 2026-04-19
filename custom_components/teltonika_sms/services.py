"""Service handlers for Teltonika SMS integration."""
from __future__ import annotations

import logging

import aiohttp
import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import (
    ATTR_MESSAGE,
    ATTR_PHONE_NUMBER,
    CONF_MODEM,
    CONF_VERIFY_SSL,
    DOMAIN,
    SERVICE_SEND_SMS,
)

_LOGGER = logging.getLogger(__name__)

SEND_SMS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PHONE_NUMBER): cv.string,
        vol.Required(ATTR_MESSAGE): cv.string,
    }
)


def _normalise_host(host: str) -> str:
    host = host.strip().rstrip("/")
    if not host.startswith(("http://", "https://")):
        host = f"http://{host}"
    return host


async def _get_token(session: aiohttp.ClientSession, host: str, username: str, password: str) -> str:
    """Authenticate and return a bearer token."""
    async with session.post(
        f"{host}/api/login",
        json={"username": username, "password": password},
        timeout=aiohttp.ClientTimeout(total=10),
    ) as resp:
        if resp.status != 200:
            raise HomeAssistantError(
                f"Teltonika SMS: Login failed (HTTP {resp.status})"
            )
        data = await resp.json(content_type=None)
        if not data.get("success"):
            errors = data.get("errors", [])
            raise HomeAssistantError(
                f"Teltonika SMS: Authentication failed – {errors}"
            )
        return data["data"]["token"]


async def _send_sms(
    session: aiohttp.ClientSession,
    host: str,
    token: str,
    number: str,
    message: str,
    modem: str,
) -> None:
    """Send the SMS message using the Teltonika API."""
    async with session.post(
        f"{host}/api/messages/actions/send",
        json={"data": {"number": number, "message": message, "modem": modem}},
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        timeout=aiohttp.ClientTimeout(total=30),
    ) as resp:
        result = await resp.json(content_type=None)
        if not result.get("success"):
            errors = result.get("errors", [])
            raise HomeAssistantError(
                f"Teltonika SMS: Failed to send SMS – {errors}"
            )
        _LOGGER.info(
            "Teltonika SMS: Message sent to %s (modem %s)", number, modem
        )


async def async_register_services(hass: HomeAssistant) -> None:
    """Register the send_sms service with Home Assistant."""

    async def handle_send_sms(call: ServiceCall) -> None:
        """Handle the send_sms service call."""
        phone_number: str = call.data[ATTR_PHONE_NUMBER]
        message: str = call.data[ATTR_MESSAGE]

        if DOMAIN not in hass.data or not hass.data[DOMAIN]:
            raise HomeAssistantError(
                "Teltonika SMS is not configured. "
                "Please add the integration via Settings → Integrations."
            )

        entry_data = next(iter(hass.data[DOMAIN].values()))
        host = _normalise_host(entry_data[CONF_HOST])
        username = entry_data[CONF_USERNAME]
        password = entry_data[CONF_PASSWORD]
        modem = entry_data.get(CONF_MODEM, "1-1")
        verify_ssl = entry_data.get(CONF_VERIFY_SSL, False)

        connector = aiohttp.TCPConnector(ssl=verify_ssl)
        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                token = await _get_token(session, host, username, password)
                await _send_sms(session, host, token, phone_number, message, modem)
            except HomeAssistantError:
                raise
            except aiohttp.ClientConnectionError as exc:
                raise HomeAssistantError(
                    f"Teltonika SMS: Cannot connect to router at {host} – {exc}"
                ) from exc
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.exception("Teltonika SMS: Unexpected error")
                raise HomeAssistantError(
                    f"Teltonika SMS: Unexpected error – {exc}"
                ) from exc

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_SMS,
        handle_send_sms,
        schema=SEND_SMS_SCHEMA,
    )
