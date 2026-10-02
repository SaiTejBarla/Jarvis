"""
tools/home_assistant.py — Home Assistant integration for JARVIS (Phase 7).

Controls smart home devices via the local Home Assistant REST API.
Home Assistant is free and runs locally — https://www.home-assistant.io

Setup:
  1. Install Home Assistant (free) on a Raspberry Pi or any PC
  2. Create a Long-Lived Access Token in HA Settings → Profile → Security
  3. Add to .env:
       HA_URL=http://homeassistant.local:8123
       HA_TOKEN=your_long_lived_token_here

Commands:
    "turn on living room light"
    "turn off bedroom fan"
    "set thermostat to 22"
    "what's the temperature sensor in kitchen"
    "list my home devices"
"""

import logging
import re
import os
from typing import Optional
from .base import BaseTool

logger = logging.getLogger(__name__)


def _ha_config() -> tuple[Optional[str], Optional[str]]:
    url = os.getenv("HA_URL", "").rstrip("/")
    token = os.getenv("HA_TOKEN", "")
    return (url or None, token or None)


class HomeAssistantTool(BaseTool):
    name = "home_assistant"
    description = (
        "Control smart home devices via Home Assistant. "
        "e.g. 'turn on living room light', 'set thermostat to 22', 'list my devices'."
    )

    def run(self, query: str) -> str:
        url, token = _ha_config()
        if not url or not token:
            return (
                "Home Assistant is not configured, Sir. "
                "Add HA_URL and HA_TOKEN to your .env file."
            )

        q = query.lower().strip()

        # List devices / entities
        if re.search(r"\b(list|show|what).{0,10}(device|light|switch|sensor|entity)\b", q):
            return self._list_entities(url, token)

        # Turn on
        if re.search(r"\bturn\s+on\b", q):
            entity = self._extract_entity(q, action="turn_on")
            return self._call_service(url, token, "homeassistant", "turn_on", entity)

        # Turn off
        if re.search(r"\bturn\s+off\b", q):
            entity = self._extract_entity(q, action="turn_off")
            return self._call_service(url, token, "homeassistant", "turn_off", entity)

        # Toggle
        if re.search(r"\btoggle\b", q):
            entity = self._extract_entity(q, action="toggle")
            return self._call_service(url, token, "homeassistant", "toggle", entity)

        # Set thermostat / climate temperature
        m = re.search(r"set\s+(?:the\s+)?(?:thermostat|temperature|temp)\s+to\s+(\d+)", q)
        if m:
            temp = m.group(1)
            entity = self._extract_entity(q, action="set temperature")
            return self._set_temperature(url, token, entity, float(temp))

        # Read a sensor
        if re.search(r"\b(temperature|humidity|motion|sensor)\b", q):
            entity = self._extract_entity(q)
            return self._get_state(url, token, entity)

        return "I didn't understand that home automation command, Sir."

    def _list_entities(self, url: str, token: str) -> str:
        try:
            import requests
            resp = requests.get(
                f"{url}/api/states",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5,
            )
            resp.raise_for_status()
            states = resp.json()
            lights = [s["entity_id"] for s in states if s["entity_id"].startswith("light.")]
            switches = [s["entity_id"] for s in states if s["entity_id"].startswith("switch.")]
            sensors = [s["entity_id"] for s in states if s["entity_id"].startswith("sensor.")]
            lines = [f"Found {len(states)} entities, Sir:"]
            if lights:
                lines.append(f"  Lights ({len(lights)}): {', '.join(lights[:5])}")
            if switches:
                lines.append(f"  Switches ({len(switches)}): {', '.join(switches[:5])}")
            if sensors:
                lines.append(f"  Sensors ({len(sensors)}): {', '.join(sensors[:5])}")
            return "\n".join(lines)
        except Exception as exc:
            return f"Could not reach Home Assistant: {exc}"

    def _call_service(self, url: str, token: str, domain: str, service: str,
                      entity_id: Optional[str]) -> str:
        try:
            import requests
            payload = {}
            if entity_id:
                payload["entity_id"] = entity_id
            resp = requests.post(
                f"{url}/api/services/{domain}/{service}",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
                timeout=5,
            )
            resp.raise_for_status()
            action = service.replace("_", " ")
            target = entity_id or "device"
            return f"Done — {action} for {target}, Sir."
        except Exception as exc:
            return f"Home Assistant command failed: {exc}"

    def _set_temperature(self, url: str, token: str,
                         entity_id: Optional[str], temp: float) -> str:
        try:
            import requests
            payload = {"temperature": temp}
            if entity_id:
                payload["entity_id"] = entity_id
            resp = requests.post(
                f"{url}/api/services/climate/set_temperature",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
                timeout=5,
            )
            resp.raise_for_status()
            return f"Temperature set to {int(temp)}°, Sir."
        except Exception as exc:
            return f"Could not set temperature: {exc}"

    def _get_state(self, url: str, token: str, entity_id: Optional[str]) -> str:
        if not entity_id:
            return "Please specify a device or sensor, Sir."
        try:
            import requests
            resp = requests.get(
                f"{url}/api/states/{entity_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
            state = data.get("state", "unknown")
            attrs = data.get("attributes", {})
            unit = attrs.get("unit_of_measurement", "")
            return f"{entity_id}: {state}{unit}"
        except Exception as exc:
            return f"Could not read {entity_id}: {exc}"

    def _extract_entity(self, q: str, action: str = "") -> Optional[str]:
        """Try to guess the entity_id from the query."""
        # Remove action words to get the device name
        cleaned = re.sub(
            r"\b(turn|on|off|toggle|set|the|my|a|an|to|and|please|"
            r"temperature|thermostat|temp|light|switch|fan|sensor|device)\b",
            " ", q
        ).strip()
        cleaned = re.sub(r"\s+", "_", cleaned).strip("_")
        if not cleaned:
            return None
        # Try common domain prefixes
        for domain in ("light", "switch", "climate", "sensor", "fan", "cover"):
            if domain in q:
                return f"{domain}.{cleaned}"
        return f"homeassistant.{cleaned}"
