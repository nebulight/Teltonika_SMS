"""Constants for Teltonika SMS integration."""

DOMAIN = "teltonika_sms"

# These are in addition to homeassistant.const CONF_HOST / CONF_USERNAME / CONF_PASSWORD
CONF_MODEM = "modem"
CONF_VERIFY_SSL = "verify_ssl"

SERVICE_SEND_SMS = "send_sms"
ATTR_PHONE_NUMBER = "phone_number"
ATTR_MESSAGE = "message"
