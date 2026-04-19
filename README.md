# Teltonika SMS — Home Assistant Integration

<p align="center">
  <img src="hacs_assets/icon.svg" alt="Teltonika SMS icon" width="140"/>
</p>

<p align="center">
  Send SMS messages through your Teltonika router (RUTX11 and compatible) directly from Home Assistant automations and scripts.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/HACS-Custom-orange?style=flat-square" alt="HACS: Custom"/>
  <img src="https://img.shields.io/badge/HA-2023.1%2B-blue?style=flat-square" alt="Home Assistant 2023.1+"/>
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT License"/>
</p>

---

## Features

- **Send SMS from any automation or script** — appears as a native action in the automation editor
- **Simple setup** via the Home Assistant UI (no YAML config required)
- **Uses the Teltonika REST API** (RutOS 7.14+ / API v1.6+)
- **Connection validated at setup** — instant feedback if credentials are wrong
- **No cloud dependency** — communicates directly with your router on your local network

---

## Supported devices

Any Teltonika router running **RutOS 7.14 or later** with the REST API enabled, including:

- RUTX11
- RUTX50
- RUTX12
- RUTX14
- RUT360
- RUT241
- TRB140 and other TRB-series gateways

---

## Prerequisites

- Home Assistant **2023.1** or later
- A Teltonika router on the same network as your HA instance (or accessible via a routable IP)
- Router admin credentials
- The REST API enabled on the router (enabled by default in RutOS 7.14+)

> **RutOS version note:** The legacy HTTP GET/POST SMS method was removed in RutOS 7.14. This integration uses the new `/api/` REST endpoint and requires RutOS 7.14 or later.

---

## Installation

### Via HACS (recommended)

1. Open HACS in Home Assistant.
2. Go to **Integrations** → click the three-dot menu → **Custom repositories**.
3. Add this repository URL and select category **Integration**.
4. Search for **Teltonika SMS** and click **Download**.
5. Restart Home Assistant.

### Manual installation

1. Download or clone this repository.
2. Copy the `custom_components/teltonika_sms/` folder into your HA config directory:
   ```
   /config/custom_components/teltonika_sms/
   ```
3. Restart Home Assistant.

---

## Configuration

1. Go to **Settings → Integrations → Add Integration**.
2. Search for **Teltonika SMS**.
3. Fill in the form:

   | Field | Description | Example |
   |---|---|---|
   | Router IP / Hostname | IP address or hostname of your router | `192.168.1.1` |
   | Username | Router admin username | `admin` |
   | Password | Router admin password | *(your password)* |
   | Modem ID | Modem identifier on the router | `3-1` |
   | Verify SSL | Validate SSL certificate (leave off for HTTP) | off |

4. Click **Submit** — the integration will test the connection before saving.

### Finding your Modem ID

The modem ID is almost always `1-1` on single-modem devices like the RUTX11. To confirm, SSH into your router and run:

```sh
cat /etc/board.json | jsonfilter -e '@.modems[0].id'
```

---

## Usage

Once configured, the **Teltonika SMS: Send SMS** action is available everywhere actions can be used in Home Assistant.

### Automation editor

In the visual automation editor, add an action, search for **Send SMS**, and fill in the phone number and message fields.

### YAML

```yaml
action: teltonika_sms.send_sms
data:
  phone_number: "+12025551234"
  message: "Motion detected at the front door!"
```

### Example automation

```yaml
alias: Alert on door open
trigger:
  - platform: state
    entity_id: binary_sensor.front_door
    to: "on"
action:
  - action: teltonika_sms.send_sms
    data:
      phone_number: "+12025551234"
      message: "Front door opened at {{ now().strftime('%H:%M') }}"
```

---

## How it works

The integration authenticates with the Teltonika REST API using a two-step process on every SMS send:

1. **POST** `/api/login` with your credentials → receives a short-lived bearer token.
2. **POST** `/api/messages/actions/send` with the token → sends the SMS via the router's modem.

This means you never need to worry about session expiry — a fresh token is fetched automatically each time.

---

## Troubleshooting

**"Cannot connect to router"**
- Verify the router IP is correct and reachable from your HA instance.
- Check that the REST API is enabled: on the router go to **Services → API**.

**"Authentication failed"**
- Double-check the username and password.
- Note that some router configurations require the `admin` role to send SMS via the API.

**"No arguments provided for action" error in logs**
- This indicates the JSON body format is wrong. Ensure you are on the latest version of this integration — earlier versions had a missing `data` wrapper.

**Modem ID issues**
- SSH in and run `cat /etc/board.json | jsonfilter -e '@.modems[0].id'` to get the exact ID for your device.

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## Credits

Built using the [Teltonika Networks REST API](https://developers.teltonika-networks.com). Not affiliated with or endorsed by Teltonika Networks.
