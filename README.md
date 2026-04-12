<div align="center">

# nonebot-plugin-bililive

_✨ 将 B 站 UP 主动态与直播推送到 QQ 的 NoneBot2 插件 ✨_

<a href="./LICENSE">
	<img src="https://img.shields.io/github/license/Akiyy-dev/nonebot-plugin-bililive.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-bililive">
	<img src="https://img.shields.io/pypi/v/nonebot-plugin-bililive.svg" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="python">
<a href="https://jq.qq.com/?_wv=1027&k=sHPbCRAd">
	<img src="https://img.shields.io/badge/QQ%E7%BE%A4-629574472-orange" alt="qq group">
</a>

</div>

> 当前仓库已按 NoneBot 插件模板整理，可直接作为插件包发布到 PyPI 并在 NoneBot2 项目中安装使用。

<details>
<summary>配置发布工作流</summary>

1. 前往 https://pypi.org/manage/account/#api-tokens 创建新的 PyPI API Token。
2. 打开当前 GitHub 仓库的 Settings - Secrets and variables - Actions。
3. 新建名为 PYPI_API_TOKEN 的 Repository Secret，并填入刚刚创建的 Token。

</details>

> [!IMPORTANT]
> 当前项目使用符合 PEP 621 的 pyproject.toml，并已补充基于 tag 触发的 PyPI 发布工作流。

<details>
<summary>触发发布</summary>

创建 tag：

	git tag v1.6.0post5

推送 tag：

	git push origin --tags

</details>

## 📖 介绍

BiliLive 是一个基于 NoneBot2 的 B 站推送插件，支持将 UP 主的直播与动态消息推送到 QQ 群或私聊场景。当前项目已将发布名、插件入口、核心实现包和工作流统一整理为 nonebot-plugin-bililive，便于作为独立插件分发。

### 特性

- 支持按 UP 主维度分别开启或关闭动态、直播推送。
- 支持群内管理员权限控制，限制机器人使用范围。
- 支持直播或动态推送时尝试 @全体成员。
- 支持多 Bot 推送失败回退与基础异常清理。
- 支持 Playwright 截图与验证码服务接入。

## 💿 安装

<details open>
<summary>使用 nb-cli 安装</summary>

在 NoneBot2 项目根目录执行：

	nb plugin install nonebot-plugin-bililive

</details>

<details>
<summary>使用包管理器安装</summary>

<details>
<summary>pip</summary>

	pip install nonebot-plugin-bililive

</details>

<details>
<summary>pdm</summary>

	pdm add nonebot-plugin-bililive

</details>

<details>
<summary>poetry</summary>

	poetry add nonebot-plugin-bililive

</details>

</details>

安装后，在 NoneBot2 项目的 pyproject.toml 中加入：

	plugins = ["nonebot_plugin_bililive"]

## ⚙️ 配置

在 NoneBot2 项目的 .env 文件中按需添加配置项：

| 配置项 | 必填 | 默认值 | 说明 |
|:-----:|:----:|:----:|:----|
| BILILIVE_DIR | 否 | data | 数据目录 |
| BILILIVE_TO_ME | 否 | true | 是否需要 @机器人 或命令前缀触发 |
| BILILIVE_PROXY | 否 | 无 | HTTP 代理地址，用于 B 站请求和 Playwright 下载 |
| BILILIVE_INTERVAL | 否 | 10 | 默认轮询间隔，单位秒 |
| BILILIVE_LIVE_INTERVAL | 否 | 10 | 直播轮询间隔，单位秒 |
| BILILIVE_DYNAMIC_INTERVAL | 否 | 0 | 动态轮询间隔，单位秒，0 表示使用默认逻辑 |
| BILILIVE_DYNAMIC_AT | 否 | false | 动态推送时是否尝试 @全体 |
| BILILIVE_LIVE_OFF_NOTIFY | 否 | false | 是否推送下播通知 |
| BILILIVE_CAPTCHA_ADDRESS | 否 | https://captcha-cd.ngworks.cn | 验证码识别服务地址 |
| BILILIVE_CAPTCHA_TOKEN | 否 | bililive | 验证码服务 token |
| BILILIVE_DYNAMIC_TIMEOUT | 否 | 30 | 动态截图超时时间，单位秒 |
| BILILIVE_DYNAMIC_FONT_SOURCE | 否 | system | 截图字体来源 |
| BILILIVE_DYNAMIC_FONT | 否 | Noto Sans CJK SC | 截图字体 |
| BILILIVE_DYNAMIC_BIG_IMAGE | 否 | false | 是否优先展示大图 |
| BILILIVE_COMMAND_PREFIX | 否 | 空字符串 | 命令额外前缀 |

## 🎉 使用

### 指令表

| 指令 | 权限 | 需要@ | 范围 | 说明 |
|:-----:|:----:|:----:|:----:|:----|
| 帮助 | 群员 | 视 BILILIVE_TO_ME 而定 | 群聊/私聊 | 查看帮助信息 |
| 关注 UID | 群员/管理员 | 视 BILILIVE_TO_ME 而定 | 群聊/私聊 | 订阅指定 UP |
| 取关 UID | 群员/管理员 | 视 BILILIVE_TO_ME 而定 | 群聊/私聊 | 取消订阅 |
| 关注列表 | 群员/管理员 | 视 BILILIVE_TO_ME 而定 | 群聊/私聊 | 查看当前订阅 |
| 开启直播 UID | 群员/管理员 | 视 BILILIVE_TO_ME 而定 | 群聊/私聊 | 开启某 UP 的直播推送 |
| 关闭直播 UID | 群员/管理员 | 视 BILILIVE_TO_ME 而定 | 群聊/私聊 | 关闭某 UP 的直播推送 |
| 开启动态 UID | 群员/管理员 | 视 BILILIVE_TO_ME 而定 | 群聊/私聊 | 开启某 UP 的动态推送 |
| 关闭动态 UID | 群员/管理员 | 视 BILILIVE_TO_ME 而定 | 群聊/私聊 | 关闭某 UP 的动态推送 |
| 开启全体 UID | 管理员 | 视 BILILIVE_TO_ME 而定 | 群聊 | 开启直播推送 @全体 |
| 关闭全体 UID | 管理员 | 视 BILILIVE_TO_ME 而定 | 群聊 | 关闭直播推送 @全体 |
| 开启权限 | 管理员 | 视 BILILIVE_TO_ME 而定 | 群聊 | 限制仅管理员可使用 |
| 关闭权限 | 管理员 | 视 BILILIVE_TO_ME 而定 | 群聊 | 关闭管理员权限限制 |
| 已开播 | 群员/管理员 | 视 BILILIVE_TO_ME 而定 | 群聊/私聊 | 查看已开播关注列表 |

### 效果图

![demo](/docs/.vuepress/public/demo.png)

## 开发

本仓库保留了本地开发启动方式：

	python bot.py

用于发布的插件入口模块为：

	nonebot_plugin_bililive

## 致谢

- [NoneBot2](https://github.com/nonebot/nonebot2)
- [go-cqhttp](https://github.com/Mrs4s/go-cqhttp)
- [bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect)
- [bilireq](https://github.com/SK-415/bilireq)

## 许可证

本项目使用 [GNU AGPLv3](https://choosealicense.com/licenses/agpl-3.0/) 作为开源许可证。
