from typing import Optional

from loguru import logger
from nonebot import get_driver
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator


# 其他地方出现的类似 from .. import config，均是从 __init__.py 导入的 Config 实例
class Config(BaseModel):
    model_config = ConfigDict(extra="ignore")

    fastapi_reload: bool = False
    haruka_dir: Optional[str] = None
    haruka_to_me: bool = True
    haruka_live_off_notify: bool = False
    haruka_proxy: Optional[str] = None
    haruka_interval: int = 10
    haruka_live_interval: int = haruka_interval
    haruka_dynamic_interval: int = 0
    haruka_dynamic_at: bool = False
    haruka_screenshot_style: str = "mobile"
    haruka_captcha_address: str = "https://captcha-cd.ngworks.cn"
    haruka_captcha_token: str = "harukabot"
    haruka_browser_ua: Optional[str] = None
    haruka_dynamic_timeout: int = 30
    haruka_dynamic_font_source: str = "system"
    haruka_dynamic_font: Optional[str] = "Noto Sans CJK SC"
    haruka_dynamic_big_image: bool = False
    haruka_command_prefix: str = ""

    @field_validator(
        "haruka_interval", "haruka_live_interval", "haruka_dynamic_interval"
    )
    @classmethod
    def non_negative(cls, v: int, info: ValidationInfo):
        """定时器为负返回默认值"""
        default = cls.model_fields[info.field_name].default
        return default if v < 1 else v

    @field_validator("haruka_screenshot_style")
    @classmethod
    def screenshot_style(cls, v: str):
        if v != "mobile":
            logger.warning("截图样式目前只支持 mobile，pc 样式现已被弃用")
        return "mobile"


global_config = get_driver().config
if hasattr(global_config, "model_dump"):
    plugin_config = Config.model_validate(global_config.model_dump())
elif hasattr(global_config, "dict"):
    plugin_config = Config.model_validate(global_config.dict())
else:
    plugin_config = Config.model_validate(global_config)
