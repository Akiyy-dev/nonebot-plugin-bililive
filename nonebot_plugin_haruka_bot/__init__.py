from nonebot.plugin import PluginMetadata
from nonebot.plugin.manager import PluginLoader

from haruka_bot import VERSION, __version__, bootstrap_plugin
from haruka_bot.config import Config, plugin_config

if isinstance(globals()["__loader__"], PluginLoader):
    bootstrap_plugin(force=True)

__plugin_meta__ = PluginMetadata(
    name="HarukaBot",
    description="将 B 站 UP 主的动态和直播信息推送至 QQ",
    usage="发送 帮助 查看命令列表",
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

__all__ = ["__plugin_meta__", "__version__", "VERSION", "plugin_config"]
