from .compat import patch_httpx_compat
from nonebot.plugin import PluginMetadata
from nonebot.plugin.manager import PluginLoader
from .config import Config

patch_httpx_compat()

def bootstrap_plugin(force: bool = False):
    if force or isinstance(globals()["__loader__"], PluginLoader):
        from .utils import on_startup

        on_startup()

        from . import plugins  # noqa: F401


bootstrap_plugin()

from .version import VERSION, __version__  # noqa: F401

__plugin_meta__ = PluginMetadata(
    name="haruka_bot",
    description="将B站UP主的动态和直播信息推送至QQ",
    usage="https://haruka-bot.sk415.icu/",
    homepage="https://github.com/SK-415/HarukaBot",
    type="application",
    config=Config,
    supported_adapters={"~onebot.v11"},
    extra={
        "author": "SK-415",
        "version": __version__,
        "priority": 1,
    },
)
