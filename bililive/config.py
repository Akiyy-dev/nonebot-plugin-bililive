
from loguru import logger
from nonebot import get_driver
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
)


def compat_field(default, new_name: str, legacy_name: str):
    return Field(
        default=default,
        validation_alias=AliasChoices(new_name, legacy_name),
    )


# 其他地方出现的类似 from .. import config，均是从 __init__.py 导入的 Config 实例
class Config(BaseModel):
    model_config = ConfigDict(extra="ignore")

    fastapi_reload: bool = False
    bililive_dir: str | None = compat_field(None, "bililive_dir", "haruka_dir")
    bililive_to_me: bool = compat_field(True, "bililive_to_me", "haruka_to_me")
    bililive_live_off_notify: bool = compat_field(
        False,
        "bililive_live_off_notify",
        "haruka_live_off_notify",
    )
    bililive_proxy: str | None = compat_field(
        None,
        "bililive_proxy",
        "haruka_proxy",
    )
    bililive_interval: int = compat_field(10, "bililive_interval", "haruka_interval")
    bililive_live_interval: int = compat_field(
        10,
        "bililive_live_interval",
        "haruka_live_interval",
    )
    bililive_dynamic_interval: int = compat_field(
        0,
        "bililive_dynamic_interval",
        "haruka_dynamic_interval",
    )
    bililive_dynamic_at: bool = compat_field(
        False,
        "bililive_dynamic_at",
        "haruka_dynamic_at",
    )
    bililive_screenshot_style: str = compat_field(
        "mobile",
        "bililive_screenshot_style",
        "haruka_screenshot_style",
    )
    bililive_captcha_address: str = compat_field(
        "https://captcha-cd.ngworks.cn",
        "bililive_captcha_address",
        "haruka_captcha_address",
    )
    bililive_captcha_token: str = compat_field(
        "bililive",
        "bililive_captcha_token",
        "haruka_captcha_token",
    )
    bililive_browser_ua: str | None = compat_field(
        None,
        "bililive_browser_ua",
        "haruka_browser_ua",
    )
    bililive_dynamic_timeout: int = compat_field(
        30,
        "bililive_dynamic_timeout",
        "haruka_dynamic_timeout",
    )
    bililive_dynamic_font_source: str = compat_field(
        "system",
        "bililive_dynamic_font_source",
        "haruka_dynamic_font_source",
    )
    bililive_dynamic_font: str | None = compat_field(
        "Noto Sans CJK SC",
        "bililive_dynamic_font",
        "haruka_dynamic_font",
    )
    bililive_dynamic_big_image: bool = compat_field(
        False,
        "bililive_dynamic_big_image",
        "haruka_dynamic_big_image",
    )
    bililive_command_prefix: str = compat_field(
        "",
        "bililive_command_prefix",
        "haruka_command_prefix",
    )

    @field_validator(
        "bililive_interval", "bililive_live_interval", "bililive_dynamic_interval"
    )
    @classmethod
    def non_negative(cls, v: int, info: ValidationInfo):
        """定时器为负返回默认值"""
        default = cls.model_fields[info.field_name].default
        return default if v < 1 else v

    @field_validator("bililive_screenshot_style")
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
