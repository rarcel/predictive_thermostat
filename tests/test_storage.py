"""Control records migrate without losing their safety flags."""

from custom_components.predictive_thermostat.storage import ControlStore


async def test_store_v1_migration_keeps_record(hass):
    store = ControlStore(hass, "test")
    record = {"schema_version": 1, "pending": True, "heat": False}
    assert await store._async_migrate_func(1, 0, record) == record
