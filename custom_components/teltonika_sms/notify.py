"""Teltonika SMS notify platform — appears under Notifications in the action picker."""
from __future__ import annotations

import logging

from homeassistant.components.notify import (
    ATTR_TARGET,
    BaseNotificationService,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN
from .services import send_sms

_LOGGER = logging.getLogger(__name__)


async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> TeltonikaNotifyService | None:
    """Return the notify service if the integration is configured."""
    if DOMAIN not in hass.data or not hass.data[DOMAIN]:
        return None
    return TeltonikaNotifyService(hass)


class TeltonikaNotifyService(BaseNotificationService):
    """Send SMS via Teltonika router through the HA notify platform."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def async_send_message(self, message: str = "", **kwargs: any) -> None:
        """Send an SMS. The 'target' field is the phone number(s)."""
        targets = kwargs.get(ATTR_TARGET)

        if not targets:
            _LOGGER.error(
                "Teltonika SMS notify: No target phone number provided. "
                "Add 'target: \"+12025551234\"' to your action."
            )
            return

        if isinstance(targets, str):
            targets = [targets]

        for number in targets:
            _LOGGER.debug(
                "Teltonika SMS notify: Sending to %s", number
            )
            await send_sms(self.hass, number, message)
