"""Config flow for Pylontech Force H3X."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback

from .api import (
    FH3XConnectionError,
    FH3XModbusClient,
    FH3XProtocolError,
)
from .const import (
    CONF_CONTROL_PROFILE,
    CONF_DETAILED_BMS,
    CONF_ENTITY_PROFILE,
    CONF_SCAN_INTERVAL,
    CONTROL_PROFILES,
    DEFAULT_CONTROL_PROFILE,
    DEFAULT_DETAILED_BMS,
    DEFAULT_ENTITY_PROFILE,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ENTITY_PROFILES,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .profiles import apply_profiles_to_registry
from .protocol import FH3XIdentity

_LOGGER = logging.getLogger(__name__)


async def async_validate_input(
    hass: HomeAssistant, data: dict[str, Any]
) -> FH3XIdentity:
    """Connect to the device and return its stable identity."""
    client = FH3XModbusClient(data[CONF_HOST], data[CONF_PORT])
    try:
        return await client.async_read_identity()
    finally:
        await client.async_close()


class FH3XConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an FH3X config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle initial UI setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                identity = await async_validate_input(self.hass, user_input)
            except FH3XConnectionError:
                errors["base"] = "cannot_connect"
            except FH3XProtocolError:
                errors["base"] = "invalid_response"
            except Exception:
                _LOGGER.exception("Unexpected exception validating FH3X connection")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(identity.serial)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=identity.model or DEFAULT_NAME,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=65535)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow changing connection details from the UI."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                identity = await async_validate_input(self.hass, user_input)
            except FH3XConnectionError:
                errors["base"] = "cannot_connect"
            except FH3XProtocolError:
                errors["base"] = "invalid_response"
            except Exception:
                _LOGGER.exception("Unexpected exception reconfiguring FH3X")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(identity.serial)
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=user_input,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=entry.data[CONF_HOST]): str,
                    vol.Required(CONF_PORT, default=entry.data[CONF_PORT]): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=65535)
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return FH3XOptionsFlow()


class FH3XOptionsFlow(OptionsFlowWithReload):
    """Handle FH3X options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure polling behavior."""
        if user_input is not None:
            apply_profiles_to_registry(
                self.hass,
                self.config_entry,
                user_input[CONF_ENTITY_PROFILE],
                user_input[CONF_CONTROL_PROFILE],
            )
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        detailed_bms = self.config_entry.options.get(
            CONF_DETAILED_BMS, DEFAULT_DETAILED_BMS
        )
        entity_profile = self.config_entry.options.get(
            CONF_ENTITY_PROFILE, DEFAULT_ENTITY_PROFILE
        )
        control_profile = self.config_entry.options.get(
            CONF_CONTROL_PROFILE, DEFAULT_CONTROL_PROFILE
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                    vol.Required(CONF_DETAILED_BMS, default=detailed_bms): bool,
                    vol.Required(
                        CONF_ENTITY_PROFILE, default=entity_profile
                    ): vol.In(
                        {
                            ENTITY_PROFILES[0]: "Recommended (core energy only)",
                            ENTITY_PROFILES[1]: "Extended monitoring",
                            ENTITY_PROFILES[2]: "Engineering diagnostics",
                        }
                    ),
                    vol.Required(
                        CONF_CONTROL_PROFILE, default=control_profile
                    ): vol.In(
                        {
                            CONTROL_PROFILES[0]: "Energy controls only",
                            CONTROL_PROFILES[1]: "Energy and basic controls",
                            CONTROL_PROFILES[2]: "Advanced controls and schedules",
                        }
                    ),
                }
            ),
        )
