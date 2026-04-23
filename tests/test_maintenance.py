import sys
import tempfile
import unittest
from importlib import import_module
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, patch


class DummyDriver:
    config = {}

    def on_startup(self, func):
        return func

    def on_shutdown(self, func):
        return func


fake_apscheduler = ModuleType("nonebot_plugin_apscheduler")
fake_localstore = ModuleType("nonebot_plugin_localstore")


class DummyScheduler:
    def add_listener(self, *args, **kwargs):
        return None

    def add_job(self, *args, **kwargs):
        return None

    def get_job(self, *args, **kwargs):
        return None


fake_apscheduler.scheduler = DummyScheduler()


def _get_plugin_data_dir() -> Path:
    return Path(tempfile.gettempdir()) / "nonebot_plugin_bililive"


fake_localstore.get_plugin_data_dir = _get_plugin_data_dir


with patch("nonebot.get_driver", return_value=DummyDriver()), patch(
    "nonebot.get_plugin_config", side_effect=lambda cls: cls()
), patch("nonebot.require", return_value=None), patch.dict(
    sys.modules,
    {
        "nonebot_plugin_apscheduler": fake_apscheduler,
        "nonebot_plugin_localstore": fake_localstore,
    },
):
    Config = import_module("nonebot_plugin_bililive.config").Config
    core_version = import_module("nonebot_plugin_bililive.version")
    db_module = import_module("nonebot_plugin_bililive.database.db")
    web_dynamic = import_module("nonebot_plugin_bililive.libs.dynamic.web")
    plugin_entry = import_module("nonebot_plugin_bililive")
    hyphen_plugin_entry = import_module("nonebot-plugin-bililive")
    DB = db_module.DB
    models = import_module("nonebot_plugin_bililive.database.models")
    Group = models.Group
    get_path = import_module("nonebot_plugin_bililive.utils").get_path


class ConfigTests(unittest.TestCase):
    def test_negative_intervals_fall_back_to_defaults(self):
        config = Config(
            bililive_interval=-1,
            bililive_live_interval=-1,
            bililive_dynamic_interval=-1,
        )

        self.assertEqual(config.bililive_interval, 10)
        self.assertEqual(config.bililive_live_interval, 10)
        self.assertEqual(config.bililive_dynamic_interval, 0)

    def test_non_mobile_screenshot_style_is_normalized(self):
        config = Config(bililive_screenshot_style="pc")

        self.assertEqual(config.bililive_screenshot_style, "mobile")

    def test_legacy_haruka_config_names_are_still_supported(self):
        config = Config(
            **{
                "haruka_interval": -1,
                "haruka_live_interval": 12,
                "haruka_command_prefix": "hb",
            }
        )

        self.assertEqual(config.bililive_interval, 10)
        self.assertEqual(config.bililive_live_interval, 12)
        self.assertEqual(config.bililive_command_prefix, "hb")


class PluginEntryTests(unittest.TestCase):
    def test_plugin_entry_exposes_plugin_metadata(self):
        self.assertEqual(
            plugin_entry.__plugin_meta__.homepage,
            "https://github.com/Akiyy-dev/nonebot-plugin-bililive",
        )
        self.assertEqual(plugin_entry.__plugin_meta__.config, Config)
        self.assertEqual(plugin_entry.__plugin_meta__.extra["author"], "Akiyy_Lab")
        self.assertEqual(plugin_entry.__version__, core_version.__version__)
        self.assertIs(hyphen_plugin_entry.__plugin_meta__, plugin_entry.__plugin_meta__)

    def test_default_data_dir_uses_localstore(self):
        expected = _get_plugin_data_dir() / "data.sqlite3"

        self.assertEqual(Path(get_path("data.sqlite3")), expected)

    def test_pyproject_uses_direct_plugin_entrypoint(self):
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

        self.assertIn(
            'nonebot-plugin-bililive = "nonebot_plugin_bililive"',
            pyproject,
        )
        self.assertIn(
            'nonebot_plugin_bililive = "nonebot_plugin_bililive"',
            pyproject,
        )
        self.assertIn('bililive = "nonebot_plugin_bililive.__main__:main"', pyproject)
        self.assertIn('includes = ["nonebot_plugin_bililive", "nonebot-plugin-bililive"]', pyproject)
        self.assertNotIn('nonebot2[fastapi]>=', pyproject)
        self.assertNotIn('bilireq>=', pyproject)


class WebDynamicTests(unittest.TestCase):
    def test_parse_web_dynamic_items_extracts_required_fields(self):
        payload = {
            "data": {
                "items": [
                    {
                        "id_str": "1190297023030493193",
                        "type": "DYNAMIC_TYPE_DRAW",
                        "modules": {
                            "module_author": {"name": "玻啵莉Polly"},
                        },
                    }
                ]
            }
        }

        items = web_dynamic.parse_web_dynamic_items(payload)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].dynamic_id, 1190297023030493193)
        self.assertEqual(items[0].dynamic_type, "DYNAMIC_TYPE_DRAW")
        self.assertEqual(items[0].author_name, "玻啵莉Polly")

    def test_parse_web_dynamic_items_skips_invalid_items(self):
        payload = {
            "data": {
                "items": [
                    {"id_str": "bad", "type": "DYNAMIC_TYPE_DRAW", "modules": {}},
                    {
                        "id_str": "1190297023030493193",
                        "type": "DYNAMIC_TYPE_DRAW",
                        "modules": {"module_author": {}},
                    },
                ]
            }
        }

        self.assertEqual(web_dynamic.parse_web_dynamic_items(payload), [])

    def test_parse_web_dynamic_payload_raises_for_error_code(self):
        payload = {
            "code": -412,
            "message": "request was banned",
            "data": None,
        }

        with self.assertRaises(web_dynamic.WebDynamicError) as context:
            web_dynamic.parse_web_dynamic_payload(payload)

        self.assertEqual(context.exception.code, -412)


class DBPermissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_db_init_enables_global_fallback(self):
        with (
            patch.object(db_module.Tortoise, "init", new=AsyncMock()) as init_db,
            patch.object(
                db_module.Tortoise,
                "generate_schemas",
                new=AsyncMock(),
            ) as generate_schemas,
            patch.object(DB, "migrate", new=AsyncMock()) as migrate,
            patch.object(DB, "update_uid_list", new=AsyncMock()) as update_uid_list,
        ):
            await DB.init()

        self.assertTrue(init_db.await_args.kwargs["_enable_global_fallback"])
        self.assertTrue(DB._ready)
        generate_schemas.assert_awaited_once()
        migrate.assert_awaited_once()
        update_uid_list.assert_awaited_once()

    async def test_wait_until_ready_returns_false_before_init(self):
        DB._ready = False

        ready = await DB.wait_until_ready(timeout=0)

        self.assertFalse(ready)

    async def test_dynamic_offsets_are_persisted_and_restored(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            offset_path = Path(tmpdir) / "dynamic_offset.json"
            db_module.dynamic_offset.clear()
            db_module.dynamic_offset[123] = 456

            with patch.object(db_module, "get_path", return_value=str(offset_path)):
                await DB.save_dynamic_offsets()

                db_module.dynamic_offset.clear()
                db_module.dynamic_offset[123] = -1
                db_module.dynamic_offset[789] = -1
                await DB.load_dynamic_offsets()

            self.assertEqual(db_module.dynamic_offset[123], 456)
            self.assertEqual(db_module.dynamic_offset[789], -1)

    async def test_set_permission_creates_group_when_missing(self):
        with (
            patch.object(DB, "get_group", new=AsyncMock(return_value=None)),
            patch.object(DB, "add_group", new=AsyncMock(return_value=True)) as add_group,
            patch.object(Group, "update", new=AsyncMock()) as update,
        ):
            changed = await DB.set_permission(123, True)

        self.assertTrue(changed)
        add_group.assert_awaited_once_with(id=123, admin=True)
        update.assert_not_awaited()

    async def test_set_permission_updates_existing_group_when_state_changes(self):
        group = SimpleNamespace(admin=False)
        with (
            patch.object(DB, "get_group", new=AsyncMock(return_value=group)),
            patch.object(Group, "update", new=AsyncMock()) as update,
        ):
            changed = await DB.set_permission(123, True)

        self.assertTrue(changed)
        update.assert_awaited_once_with({"id": 123}, admin=True)

    async def test_set_permission_is_noop_when_state_matches(self):
        group = SimpleNamespace(admin=False)
        with (
            patch.object(DB, "get_group", new=AsyncMock(return_value=group)),
            patch.object(Group, "update", new=AsyncMock()) as update,
        ):
            changed = await DB.set_permission(123, False)

        self.assertFalse(changed)
        update.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
