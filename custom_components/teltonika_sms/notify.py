"""Teltonika SMS notify entity platform.

Registers a NotifyEntity so the integration appears under
Notifications → "Send a notification via teltonika_sms" in the action picker.
"""
from __future__ import annotations

import logging

from homeassistant.components.notify import NotifyEntity, NotifyEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_MODEM, DOMAIN
from .services import send_sms

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Teltonika SMS notify entity from a config entry."""
    async_add_entities([TeltonikaNotifyEntity(hass, entry)])


class TeltonikaNotifyEntity(NotifyEntity):
    """A notify entity that sends SMS via a Teltonika router."""

    _attr_has_entity_name = True
    _attr_name = None          # uses device name as entity name
    _attr_icon = "mdi:message-text"
    _attr_supported_features = NotifyEntityFeature.TITLE

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_notify"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Teltonika SMS",
            manufacturer="Teltonika Networks",
            model=entry.data.get(CONF_MODEM, "RUTX11"),
        )

    async def async_send_message(
        self, message: str, title: str | None = None, recipient: str | None = None
    ) -> None:
        """Send an SMS message.

        The phone number goes in the 'recipient' field (or 'target' in legacy YAML).
        If a title is provided it is prepended to the message.
        """
        if not recipient:
            _LOGGER.error(
                "Teltonika SMS: 'recipient' (phone number) is required. "
                "Example: recipient: '+12025551234'"
            )
            return

        full_message = f"{title}: {message}" if title else message
        await send_sms(self.hass, recipient, full_message)
