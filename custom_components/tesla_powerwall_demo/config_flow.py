"""Config flow for the Tesla Powerwall demo integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigFlow

from .const import DOMAIN


class TeslaPowerwallDemoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a demo Powerwall setup."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Create the simulated Powerwall device."""
        if user_input is not None:
            return self.async_create_entry(
                title="Tesla Powerwall（模拟设备）", data={}
            )

        return self.async_show_form(step_id="user")
