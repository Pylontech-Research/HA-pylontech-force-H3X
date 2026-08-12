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
from .discovery import FH3XDiscoveryInfo, async_discover_fh3x
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

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discoveries: dict[str, FH3XDiscoveryInfo] = {}
        self._pending_data: dict[str, Any] | None = None
        self._pending_identity: FH3XIdentity | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Discover FH3X devices when the integration is added."""
        # Preserve compatibility with flows/tests that submit the former user
        # form directly instead of entering through the frontend.
        if user_input is not None and CONF_HOST in user_input:
            return await self.async_step_manual(user_input)
        return await self.async_step_scan()

    async def async_step_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Actively scan all enabled local IPv4 networks."""
        del user_input
        try:
            discoveries = await async_discover_fh3x(self.hass)
        except Exception:
            _LOGGER.exception("Unexpected exception discovering FH3X devices")
            discoveries = []

        self._discoveries = {
            f"{discovery.usn or ''}|{discovery.host}": discovery
            for discovery in discoveries
        }
        if not self._discoveries:
            return await self.async_step_discovery_failed()
        if len(self._discoveries) == 1:
            return await self._async_accept_discovery(
                next(iter(self._discoveries.values()))
            )
        return await self.async_step_select_device()

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user select one of multiple discovered devices."""
        errors: dict[str, str] = {}
        if user_input is not None:
            selected = self._discoveries.get(user_input["device"])
            if selected is None:
                errors["base"] = "discovery_expired"
            else:
                return await self._async_accept_discovery(selected)

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema(
                {
                    vol.Required("device"): vol.In(
                        {
                            key: discovery.display_name
                            for key, discovery in self._discoveries.items()
                        }
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_discovery_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer another scan or manual setup after discovery fails."""
        del user_input
        return self.async_show_menu(
            step_id="discovery_failed",
            menu_options=["scan", "manual"],
        )

    async def async_step_discovery_validation_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer recovery after discovery validation fails."""
        if user_input is not None:
            next_step = user_input.get("next_step_id")
            if next_step == "scan":
                return await self.async_step_scan()
            if next_step == "manual":
                return await self.async_step_manual()
        return self.async_show_menu(
            step_id="discovery_validation_failed",
            menu_options=["scan", "manual"],
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual IP setup as a discovery fallback."""
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
            step_id="manual",
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

    async def _async_accept_discovery(
        self, discovery: FH3XDiscoveryInfo
    ) -> ConfigFlowResult:
        """Accept an SSDP candidate without blocking on Modbus validation."""
        data = {CONF_HOST: discovery.host, CONF_PORT: discovery.port}
        serial = discovery.usn or discovery.host
        identity = FH3XIdentity(
            manufacturer="Pylontech",
            model=discovery.server or DEFAULT_NAME,
            serial=f"ssdp-{serial}",
            software_version="unknown",
        )
        await self.async_set_unique_id(identity.serial, raise_on_progress=False)
        self._pending_data = data
        self._pending_identity = identity
        self.context["title_placeholders"] = {"name": identity.model}
        return await self.async_step_confirm()

    async def _async_validate_discovery(
        self, discovery: FH3XDiscoveryInfo
    ) -> ConfigFlowResult:
        """Compatibility wrapper for callers using the former method name."""
        return await self._async_accept_discovery(discovery)

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered FH3X before creating the config entry."""
        if self._pending_data is None or self._pending_identity is None:
            return self.async_abort(reason="discovery_expired")
        if user_input is not None:
            return self.async_create_entry(
                title=self._pending_identity.model or DEFAULT_NAME,
                data=self._pending_data,
            )
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "model": self._pending_identity.model or DEFAULT_NAME,
                "serial": self._pending_identity.serial,
                "host": self._pending_data[CONF_HOST],
            },
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
                    vol.Required(CONF_ENTITY_PROFILE, default=entity_profile): vol.In(
                        {
                            ENTITY_PROFILES[0]: "Recommended (core energy only)",
                            ENTITY_PROFILES[1]: "Extended monitoring",
                            ENTITY_PROFILES[2]: "Engineering diagnostics",
                        }
                    ),
                    vol.Required(CONF_CONTROL_PROFILE, default=control_profile): vol.In(
                        {
                            CONTROL_PROFILES[0]: "Daily controls only",
                            CONTROL_PROFILES[1]: ("Daily controls and common settings"),
                            CONTROL_PROFILES[2]: (
                                "Advanced controls and full schedules"
                            ),
                        }
                    ),
                }
            ),
        )
