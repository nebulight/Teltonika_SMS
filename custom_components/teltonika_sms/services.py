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


async def _get_token(
    session: aiohttp.ClientSession, host: str, username: str, password: str
) -> str:
    """Authenticate against the Teltonika API and return a bearer token."""
    url = f"{host}/api/login"
    _LOGGER.debug("Teltonika SMS: Authenticating at %s as user '%s'", url, username)
    try:
        async with session.post(
            url,
            json={"username": username, "password": password},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            raw = await resp.text()
            _LOGGER.debug(
                "Teltonika SMS: Login response HTTP %s — %s", resp.status, raw
            )
            if resp.status == 403:
                raise HomeAssistantError(
                    f"Teltonika SMS: Login forbidden (HTTP 403). "
                    f"Check username/password and that the API is enabled on the router."
                )
            if resp.status != 200:
                raise HomeAssistantError(
                    f"Teltonika SMS: Unexpected login response HTTP {resp.status}. "
                    f"Body: {raw[:200]}"
                )
            try:
                data = __import__("json").loads(raw)
            except Exception:
                raise HomeAssistantError(
                    f"Teltonika SMS: Login response was not JSON. Body: {raw[:200]}"
                )
            if not data.get("success"):
                errors = data.get("errors", data)
                raise HomeAssistantError(
                    f"Teltonika SMS: Authentication failed — {errors}"
                )
            token = data.get("data", {}).get("token")
            if not token:
                raise HomeAssistantError(
                    f"Teltonika SMS: No token in login response — {data}"
                )
            _LOGGER.debug("Teltonika SMS: Login successful, token obtained")
            return token
    except HomeAssistantError:
        raise
    except aiohttp.ClientConnectionError as exc:
        raise HomeAssistantError(
            f"Teltonika SMS: Cannot reach router at {host} — {exc}. "
            f"Check the IP address and that HA can reach the router."
        ) from exc
    except aiohttp.ClientSSLError as exc:
        raise HomeAssistantError(
            f"Teltonika SMS: SSL error connecting to {host} — {exc}. "
            f"Try enabling 'Verify SSL: off' in the integration settings, "
            f"or switch to http:// instead of https://."
        ) from exc


async def _send_sms(
    session: aiohttp.ClientSession,
    host: str,
    token: str,
    number: str,
    message: str,
    modem: str,
) -> None:
    """Send the SMS message using the Teltonika API."""
    url = f"{host}/api/messages/actions/send"
    payload = {"data": {"number": number, "message": message, "modem": modem}}
    _LOGGER.debug(
        "Teltonika SMS: Sending to %s via modem %s — payload: %s",
        number, modem, payload,
    )
    try:
        async with session.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            raw = await resp.text()
            _LOGGER.debug(
                "Teltonika SMS: Send response HTTP %s — %s", resp.status, raw
            )
            if resp.status == 401:
                raise HomeAssistantError(
                    "Teltonika SMS: Unauthorised when sending (HTTP 401). "
                    "The token was rejected — this may be a permissions issue."
                )
            try:
                result = __import__("json").loads(raw)
            except Exception:
                raise HomeAssistantError(
                    f"Teltonika SMS: Send response was not JSON. Body: {raw[:200]}"
                )
            if not result.get("success"):
                errors = result.get("errors", result)
                raise HomeAssistantError(
                    f"Teltonika SMS: Router rejected the SMS — {errors}. "
                    f"Check the modem ID (currently '{modem}') and that a SIM with credit is inserted."
                )
            _LOGGER.info(
                "Teltonika SMS: ✓ Message sent to %s via modem %s", number, modem
            )
    except HomeAssistantError:
        raise
    except aiohttp.ClientConnectionError as exc:
        raise HomeAssistantError(
            f"Teltonika SMS: Connection dropped while sending — {exc}"
        ) from exc


async def send_sms(hass: HomeAssistant, phone_number: str, message: str) -> None:
    """Public helper — send an SMS using the first configured entry."""
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

    _LOGGER.debug(
        "Teltonika SMS: Using host=%s modem=%s verify_ssl=%s", host, modem, verify_ssl
    )

    connector = aiohttp.TCPConnector(ssl=verify_ssl)
    async with aiohttp.ClientSession(connector=connector) as session:
        token = await _get_token(session, host, username, password)
        await _send_sms(session, host, token, phone_number, message, modem)


async def async_register_services(hass: HomeAssistant) -> None:
    """Register the send_sms service with Home Assistant."""

    async def handle_send_sms(call: ServiceCall) -> None:
        phone_number: str = call.data[ATTR_PHONE_NUMBER]
        message: str = call.data[ATTR_MESSAGE]
        _LOGGER.debug(
            "Teltonika SMS: Service called — to=%s message=%r", phone_number, message
        )
        await send_sms(hass, phone_number, message)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_SMS,
        handle_send_sms,
        schema=SEND_SMS_SCHEMA,
    )
