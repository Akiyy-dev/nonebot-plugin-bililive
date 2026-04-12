import unittest
from importlib import import_module
from types import ModuleType
from types import SimpleNamespace
import sys
from unittest.mock import AsyncMock, patch

import httpx


class DummyDriver:
    config = {}

    def on_startup(self, func):
        return func

    def on_shutdown(self, func):
        return func


fake_apscheduler = ModuleType("nonebot_plugin_apscheduler")
fake_apscheduler.scheduler = SimpleNamespace()


with patch("nonebot.get_driver", return_value=DummyDriver()), patch(
    "nonebot.require", return_value=None
), patch.dict(sys.modules, {"nonebot_plugin_apscheduler": fake_apscheduler}):
    compat = import_module("haruka_bot.compat")
    Config = import_module("haruka_bot.config").Config
    DB = import_module("haruka_bot.database.db").DB
    models = import_module("haruka_bot.database.models")
    Group = models.Group


class ConfigTests(unittest.TestCase):
    def test_negative_intervals_fall_back_to_defaults(self):
        config = Config(
            haruka_interval=-1,
            haruka_live_interval=-1,
            haruka_dynamic_interval=-1,
        )

        self.assertEqual(config.haruka_interval, 10)
        self.assertEqual(config.haruka_live_interval, 10)
        self.assertEqual(config.haruka_dynamic_interval, 0)

    def test_non_mobile_screenshot_style_is_normalized(self):
        config = Config(haruka_screenshot_style="pc")

        self.assertEqual(config.haruka_screenshot_style, "mobile")


class CompatTests(unittest.TestCase):
    def test_httpx_compat_adds_legacy_proxy_alias(self):
        compat.patch_httpx_compat()

        self.assertTrue(hasattr(httpx._types, "ProxiesTypes"))

    def test_httpx_compat_accepts_legacy_proxies_keyword(self):
        compat.patch_httpx_compat()

        client = httpx.AsyncClient(proxies={"all://": None})
        self.assertIsInstance(client, httpx.AsyncClient)
        self.addCleanup(lambda: __import__("asyncio").run(client.aclose()))


class DBPermissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_set_permission_creates_group_when_missing(self):
        with patch.object(DB, "get_group", new=AsyncMock(return_value=None)), patch.object(
            DB, "add_group", new=AsyncMock(return_value=True)
        ) as add_group, patch.object(Group, "update", new=AsyncMock()) as update:
            changed = await DB.set_permission(123, True)

        self.assertTrue(changed)
        add_group.assert_awaited_once_with(id=123, admin=True)
        update.assert_not_awaited()

    async def test_set_permission_updates_existing_group_when_state_changes(self):
        group = SimpleNamespace(admin=False)
        with patch.object(DB, "get_group", new=AsyncMock(return_value=group)), patch.object(
            Group, "update", new=AsyncMock()
        ) as update:
            changed = await DB.set_permission(123, True)

        self.assertTrue(changed)
        update.assert_awaited_once_with({"id": 123}, admin=True)

    async def test_set_permission_is_noop_when_state_matches(self):
        group = SimpleNamespace(admin=False)
        with patch.object(DB, "get_group", new=AsyncMock(return_value=group)), patch.object(
            Group, "update", new=AsyncMock()
        ) as update:
            changed = await DB.set_permission(123, False)

        self.assertFalse(changed)
        update.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()