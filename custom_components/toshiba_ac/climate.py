"""Platform for climate integration."""

import logging
from typing import Any, List, Mapping, Optional
from homeassistant.components.climate.const import (
    CURRENT_HVAC_OFF,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_DRY,
    # CURRENT_HVAC_IDLE,
    CURRENT_HVAC_FAN,
    HVAC_MODE_OFF,
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_FAN_MODE,
    SUPPORT_SWING_MODE,
    SUPPORT_PRESET_MODE,
    # SUPPORT_AUX_HEAT,
    # FAN_AUTO,
    # FAN_DIFFUSE,
    FAN_ON,
    FAN_OFF,
    # FAN_LOW,
    # FAN_MEDIUM,
    # FAN_HIGH,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.util.temperature import convert as convert_temperature


# , TEMP_FAHRENHEIT
# from voluptuous.validators import Switch
from .const import DOMAIN

# from .toshiba_ac_control.toshiba_ac.fcu_state import ToshibaAcStatus, AcMode, AcFanMode
# from toshiba_ac.fcu_state import AcStatus, AcMode, AcFanMode
from toshiba_ac.device import (
    ToshibaAcDevice,
    ToshibaAcStatus,
    ToshibaAcPowerSelection,
    ToshibaAcSwingMode,
    ToshibaAcFanMode,
    ToshibaAcMode,
    ToshibaAcMeritA,
    ToshibaAcSelfCleaning,
)
from toshiba_ac.utils import pretty_enum_name

try:
    from homeassistant.components.climate import ClimateEntity
except ImportError:
    from homeassistant.components.climate import ClimateDevice as ClimateEntity

_LOGGER = logging.getLogger(__name__)


# This function is called as part of the __init__.async_setup_entry (via the
# hass.config_entries.async_forward_entry_setup call)
async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add climate for passed config_entry in HA."""
    # The hub is loaded from the associated hass.data entry that was created in the
    # __init__.async_setup_entry function
    device_manager = hass.data[DOMAIN][config_entry.entry_id]

    # The next few lines find all of the entities that will need to be added
    # to HA. Note these are all added to a list, so async_add_devices can be
    # called just once.
    new_devices = []

    devices = await device_manager.get_devices()
    for device in devices:
        climate_entity = ToshibaClimate(device)
        new_devices.append(climate_entity)
    # If we have any new devices, add them
    if new_devices:
        _LOGGER.info("Adding %d %s", len(new_devices), "climates")
        async_add_devices(new_devices)


class ToshibaClimate(ClimateEntity):
    """Provides a Toshiba climates."""

    # Our dummy class is PUSH, so we tell HA that it should not be polled
    should_poll = False
    # The supported features of a cover are done using a bitmask. Using the constants
    # imported above, we can tell HA the features that are supported by this entity.
    # If the supported features were dynamic (ie: different depending on the external
    # device it connected to), then this should be function with an @property decorator.
    supported_features = SUPPORT_FAN_MODE | SUPPORT_TARGET_TEMPERATURE | SUPPORT_SWING_MODE | SUPPORT_PRESET_MODE

    _device: ToshibaAcDevice = None

    # _platform = "climate"

    def __init__(self, toshiba_device: ToshibaAcDevice):
        """Initialize the climate."""
        self._device = toshiba_device

        # _LOGGER.debug("###########################")
        # _LOGGER.debug(
        #     "Supported features: ac_mode %s, ac_swing_mode %s, ac_merit_b %s, ac_merit_a %s, ac_energy_report %s",
        #     self._device.supported.ac_mode,
        #     self._device.supported.ac_swing_mode,
        #     self._device.supported.ac_merit_b,
        #     self._device.supported.ac_merit_a,
        #     # self._device.supported.ac_pure_ion,
        #     self._device.supported.ac_energy_report,
        # )

        # # _LOGGER.debug("Test get current power selection %s", self._device.ac_power_selection)
        # # _LOGGER.debug("Test get list of power selections %s", list(ToshibaAcPowerSelection))

        # # ac_power_selection_nice = [pretty_enum_name(e) for e in self._device.supported.ac_swing_mode]

        # # self._device.supported.ac_swing_mode

        # _LOGGER.debug("Test get list of swing modes %s", self.get_feature_list(self._device.supported.ac_swing_mode))

        # # _LOGGER.debug(
        # #     "Test get list of swing modes %s %s",
        # #     self._device.supported.ac_swing_mode,
        # #     list(self._device.supported.ac_swing_mode),
        # # )

        # _LOGGER.debug("###########################")

        # ToshibaEntity.__init__(self, device_id, toshibaconnection, toshibaproject, coordinator)
        # self.entity_id = "climate." + self._name.lower() + "_" + self._device_id

    # default entity properties

    async def state_changed(self, dev):
        """Whenever state should change."""
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        # Importantly for a push integration, the module that will be getting updates
        # needs to notify HA of changes. The dummy device has a registercallback
        # method, so to this we add the 'self.async_write_ha_state' method, to be
        # called where ever there are changes.
        # The call back registration is done once this entity is registered with HA
        # (rather than in the __init__)
        # self._device.register_callback(self.async_write_ha_state)
        self._device.on_state_changed_callback.add(self.state_changed)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        # The opposite of async_added_to_hass. Remove any registered call backs here.
        # self._device.remove_callback(self.async_write_ha_state)
        self._device.on_state_changed_callback.remove(self.state_changed)

    # A unique_id for this entity with in this domain. This means for example if you
    # have a sensor on this cover, you must ensure the value returned is unique,
    # which is done here by appending "_cover". For more information, see:
    # https://developers.home-assistant.io/docs/entity_registry_index/#unique-id-requirements
    # Note: This is NOT used to generate the user visible Entity ID used in automations.
    @property
    def unique_id(self):
        """Return Unique ID string."""
        return f"{self._device.ac_unique_id}_climate"

    # Information about the devices that is partially visible in the UI.
    # The most critical thing here is to give this entity a name so it is displayed
    # as a "device" in the HA UI. This name is used on the Devices overview table,
    # and the initial screen when the device is added (rather than the entity name
    # property below). You can then associate other Entities (eg: a battery
    # sensor) with this device, so it shows more like a unified element in the UI.
    # For example, an associated battery sensor will be displayed in the right most
    # column in the Configuration > Devices view for a device.
    # To associate an entity with this device, the device_info must also return an
    # identical "identifiers" attribute, but not return a name attribute.
    # See the sensors.py file for the corresponding example setup.
    # Additional meta data can also be returned here, including sw_version (displayed
    # as Firmware), model and manufacturer (displayed as <model> by <manufacturer>)
    # shown on the device info screen. The Manufacturer and model also have their
    # respective columns on the Devices overview table. Note: Many of these must be
    # set when the device is first added, and they are not always automatically
    # refreshed by HA from it's internal cache.
    # For more information see:
    # https://developers.home-assistant.io/docs/device_registry_index/#device-properties
    @property
    def device_info(self):
        """Information about this entity/device."""
        return {
            "identifiers": {(DOMAIN, self._device.ac_unique_id)},
            # If desired, the name for the device could be different to the entity
            "name": self.name,
            "account": self._device.ac_id,
            "device_id": self._device.device_id,
            "sw_version": self._device.firmware_version,
            # "model": self._roller.model,
            "manufacturer": "Toshiba",
        }

    # This is the name for this *entity*, the "name" attribute from "device_info"
    # is used as the device name for device screens in the UI. This name is used on
    # entity screens, and used to build the Entity ID that's used is automations etc.
    @property
    def name(self):
        """Return the name of the device."""
        return self._device.name

    # This property is important to let HA know if this entity is online or not.
    # If an entity is offline (return False), the UI will refelect this.
    @property
    def available(self) -> bool:
        """Return True if climate is available."""
        return self._device.ac_id and self._device.amqp_api.sas_token and self._device.http_api.access_token

    # climate properties

    # TEMPERATURE

    @property
    def is_on(self):
        """Return True if the device is on or completely off."""
        return self._device.ac_status == ToshibaAcStatus.ON

    @property
    def current_temperature(self):
        """Return current temperature."""
        return self._device.ac_indoor_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._device.ac_temperature

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 1

    @property
    def temperature_unit(self):
        """Return unit of temperature measurement for the system (TEMP_CELSIUS or TEMP_FAHRENHEIT)."""
        return TEMP_CELSIUS

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        set_temperature = kwargs.get(ATTR_TEMPERATURE)
        if set_temperature is None:
            return

        # if hasattr(self._device, "ac_merit_a") and ToshibaAcMeritA.HEATING_8C in self._device.supported.ac_merit_a:
        if hasattr(self._device, "ac_merit_a") and self._device.ac_merit_a == ToshibaAcMeritA.HEATING_8C:
            # upper limit for target temp
            if set_temperature > 13:
                set_temperature = 13
            # lower limit for target temp
            elif set_temperature < 5:
                set_temperature = 5
        else:
            # upper limit for target temp
            if set_temperature > 30:
                set_temperature = 30
            # lower limit for target temp
            elif set_temperature < 17:
                set_temperature = 17

        await self._device.set_ac_temperature(set_temperature)

    # PRESET MODE / POWER SETTING

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode, e.g., home, away, temp.

        Requires SUPPORT_PRESET_MODE.
        """
        if self._device.ac_self_cleaning == ToshibaAcSelfCleaning.ON:
            return "cleaning"

        if not self.is_on:
            return None

        return pretty_enum_name(self._device.ac_power_selection)

    @property
    def preset_modes(self) -> Optional[List[str]]:
        """Return a list of available preset modes.

        Requires SUPPORT_PRESET_MODE.
        """
        return self.get_feature_list(self._device.supported.ac_power_selection)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        _LOGGER.info("Toshiba Climate setting preset_mode: %s", preset_mode)

        feature_list_id = self.get_feature_list_id(list(ToshibaAcPowerSelection), preset_mode)
        if feature_list_id is not None:
            await self._device.set_ac_power_selection(feature_list_id)

    # AC MODES

    @property
    def hvac_mode(self):
        """Return target operation (e.g.heat, cool, auto, off). Used to determine state."""
        if not self.is_on:
            return HVAC_MODE_OFF

        if self._device.ac_mode == ToshibaAcMode.AUTO:
            return HVAC_MODE_AUTO
        elif self._device.ac_mode == ToshibaAcMode.COOL:
            return HVAC_MODE_COOL
        elif self._device.ac_mode == ToshibaAcMode.HEAT:
            return HVAC_MODE_HEAT
        elif self._device.ac_mode == ToshibaAcMode.DRY:
            return HVAC_MODE_DRY
        elif self._device.ac_mode == ToshibaAcMode.FAN:
            return HVAC_MODE_FAN_ONLY
        else:
            return HVAC_MODE_OFF

    # HVAC MODES

    @property
    def hvac_modes(self):
        """List of available operation modes. See below."""
        # button for auto is still there, to clear manual mode, but will not change highlighted icon
        # return [e.lower() for e in self.get_feature_list(self._device.supported.ac_mode)]
        available_modes = [HVAC_MODE_OFF]
        if ToshibaAcMode.AUTO in self._device.supported.ac_mode:
            available_modes.append(HVAC_MODE_AUTO)
        if ToshibaAcMode.COOL in self._device.supported.ac_mode:
            available_modes.append(HVAC_MODE_COOL)
        if ToshibaAcMode.DRY in self._device.supported.ac_mode:
            available_modes.append(HVAC_MODE_DRY)
        if ToshibaAcMode.FAN in self._device.supported.ac_mode:
            available_modes.append(HVAC_MODE_FAN_ONLY)
        if ToshibaAcMode.HEAT in self._device.supported.ac_mode:
            available_modes.append(HVAC_MODE_HEAT)

        return available_modes

    @property
    def hvac_action(self):
        """Return current HVAC action (heating, cooling, idle, off)."""
        if not self.is_on:
            return CURRENT_HVAC_OFF

        if self._device.ac_mode == ToshibaAcMode.AUTO:
            return CURRENT_HVAC_COOL  # CURRENT_HVAC_IDLE
        elif self._device.ac_mode == ToshibaAcMode.COOL:
            return CURRENT_HVAC_COOL
        elif self._device.ac_mode == ToshibaAcMode.HEAT:
            return CURRENT_HVAC_HEAT
        elif self._device.ac_mode == ToshibaAcMode.DRY:
            return CURRENT_HVAC_DRY
        elif self._device.ac_mode == ToshibaAcMode.FAN:
            return CURRENT_HVAC_FAN
        else:
            return CURRENT_HVAC_OFF

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        _LOGGER.info("Toshiba Climate setting hvac_mode: %s", hvac_mode)

        if hvac_mode == HVAC_MODE_OFF:
            await self._device.set_ac_status(ToshibaAcStatus.OFF)
        else:
            if not self.is_on:
                await self._device.set_ac_status(ToshibaAcStatus.ON)
            if hvac_mode == HVAC_MODE_AUTO:
                await self._device.set_ac_mode(ToshibaAcMode.AUTO)
            elif hvac_mode == HVAC_MODE_COOL:
                await self._device.set_ac_mode(ToshibaAcMode.COOL)
            elif hvac_mode == HVAC_MODE_HEAT:
                await self._device.set_ac_mode(ToshibaAcMode.HEAT)
            elif hvac_mode == HVAC_MODE_DRY:
                await self._device.set_ac_mode(ToshibaAcMode.DRY)
            elif hvac_mode == HVAC_MODE_FAN_ONLY:
                await self._device.set_ac_mode(ToshibaAcMode.FAN)

    # FAN MODES
    @property
    def fan_modes(self) -> Optional[List[str]]:
        """Return the list of available fan modes.

        Requires SUPPORT_FAN_MODE.
        """
        return self.get_feature_list(self._device.supported.ac_fan_mode)

    @property
    def fan_mode(self):
        """Return the current fan mode. Requires SUPPORT_FAN_MODE."""
        # return self._device.ac_fan_mode.name
        return pretty_enum_name(self._device.ac_fan_mode)

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        _LOGGER.info("Toshiba Climate setting fan_mode: %s", fan_mode)
        if fan_mode == FAN_OFF:
            await self._device.set_ac_fan_mode(ToshibaAcStatus.OFF)
        else:
            if not self.is_on:
                await self._device.set_ac_status(ToshibaAcStatus.ON)

            feature_list_id = self.get_feature_list_id(list(ToshibaAcFanMode), fan_mode)
            if feature_list_id is not None:
                await self._device.set_ac_fan_mode(feature_list_id)

    # SWING MODES
    @property
    def swing_modes(self) -> Optional[List[str]]:
        """Return the list of available swing modes.

        Requires SUPPORT_SWING_MODE.
        """
        return self.get_feature_list(self._device.supported.ac_swing_mode)

    @property
    def swing_mode(self) -> Optional[str]:
        """Return the swing setting.

        Requires SUPPORT_SWING_MODE.
        """
        return pretty_enum_name(self._device.ac_swing_mode)

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new target swing operation."""
        feature_list_id = self.get_feature_list_id(list(ToshibaAcSwingMode), swing_mode)
        if feature_list_id is not None:
            await self._device.set_ac_swing_mode(feature_list_id)

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        if hasattr(self._device, "ac_merit_a") and self._device.ac_merit_a == ToshibaAcMeritA.HEATING_8C:
            return convert_temperature(5, TEMP_CELSIUS, self.temperature_unit)
        return convert_temperature(17, TEMP_CELSIUS, self.temperature_unit)

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        if hasattr(self._device, "ac_merit_a") and self._device.ac_merit_a == ToshibaAcMeritA.HEATING_8C:
            return convert_temperature(13, TEMP_CELSIUS, self.temperature_unit)
        return convert_temperature(30, TEMP_CELSIUS, self.temperature_unit)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return entity specific state attributes.

        Implemented by platform classes. Convention for attribute names
        is lowercase snake_case.
        """
        return {
            "merit_a_feature": self._device.ac_merit_a.name,
            "merit_b_feature": self._device.ac_merit_b.name,
            "air_pure_ion": self._device.ac_air_pure_ion.name,
            "self_cleaning": self._device.ac_self_cleaning.name,
            "outdoor_temperature": self._device.ac_outdoor_temperature,
        }

    def get_feature_list(self, feature_list: List[Any]) -> List[Any]:
        """Return a list of features supported by the device."""
        return [pretty_enum_name(e) for e in feature_list if pretty_enum_name(e) != "None"]

    def get_feature_list_id(self, feature_list: List[Any], feature_name: str) -> Any:
        """Return the enum value of that item with the given name from a feature list."""
        _LOGGER.debug("searching %s for %s", feature_list, feature_name)

        feature_list = [e for e in feature_list if pretty_enum_name(e) == feature_name]
        _LOGGER.debug("and found %s", feature_list)

        if len(feature_list) > 0:
            return feature_list[0]
        else:
            return None


# end class ToshibaClimate
