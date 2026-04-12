import asyncio
from datetime import datetime
from time import monotonic

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MISSED,
    EVENT_SCHEDULER_STARTED,
)
from bilireq.exceptions import GrpcError
from bilireq.grpc.dynamic import grpc_get_user_dynamics
from bilireq.grpc.protos.bilibili.app.dynamic.v2.dynamic_pb2 import DynamicType
from grpc import StatusCode
from grpc.aio import AioRpcError
from nonebot.adapters.onebot.v11.message import MessageSegment
from nonebot.log import logger

from ...config import plugin_config
from ...database import DB as db
from ...database import dynamic_offset as offset
from ...libs.dynamic.web import WebDynamicError, get_user_dynamics_web
from ...utils import (
    get_bilibili_cookies,
    get_dynamic_screenshot,
    safe_send,
    scheduler,
)

RISK_CONTROL_RETRY_SECONDS = 3600
dynamic_risk_control_until = {}
dynamic_web_fallback_until = {}
WEB_SKIP_DYNAMIC_TYPES = {
    "DYNAMIC_TYPE_LIVE_RCMD",
    "DYNAMIC_TYPE_LIVE",
    "DYNAMIC_TYPE_AD",
    "DYNAMIC_TYPE_BANNER",
}
WEB_DYNAMIC_TYPE_MESSAGES = {
    "DYNAMIC_TYPE_FORWARD": "转发了一条动态",
    "DYNAMIC_TYPE_WORD": "发布了新文字动态",
    "DYNAMIC_TYPE_DRAW": "发布了新图文动态",
    "DYNAMIC_TYPE_AV": "发布了新投稿",
    "DYNAMIC_TYPE_ARTICLE": "发布了新专栏",
    "DYNAMIC_TYPE_MUSIC": "发布了新音频",
}


async def throttle_dynamic_loop():
    if plugin_config.bililive_dynamic_interval == 0:
        await asyncio.sleep(1)


def get_dynamic_id(dynamic, use_web_fallback: bool) -> int:
    if use_web_fallback:
        return dynamic.dynamic_id
    return int(dynamic.extend.dyn_id_str)


def get_dynamic_type(dynamic, use_web_fallback: bool):
    if use_web_fallback:
        return dynamic.dynamic_type
    return dynamic.card_type


def get_dynamic_author_name(dynamic, use_web_fallback: bool) -> str:
    if use_web_fallback:
        return dynamic.author_name
    return dynamic.modules[0].module_author.author.name


def get_dynamic_type_message(dynamic_type, use_web_fallback: bool) -> str:
    if use_web_fallback:
        return WEB_DYNAMIC_TYPE_MESSAGES.get(dynamic_type, "发布了新动态")
    return {
        0: "发布了新动态",
        DynamicType.forward: "转发了一条动态",
        DynamicType.word: "发布了新文字动态",
        DynamicType.draw: "发布了新图文动态",
        DynamicType.av: "发布了新投稿",
        DynamicType.article: "发布了新专栏",
        DynamicType.music: "发布了新音频",
    }.get(dynamic_type, "发布了新动态")


def should_skip_dynamic(dynamic_type, use_web_fallback: bool) -> bool:
    if use_web_fallback:
        return dynamic_type in WEB_SKIP_DYNAMIC_TYPES
    return dynamic_type in [
        DynamicType.live_rcmd,
        DynamicType.live,
        DynamicType.ad,
        DynamicType.banner,
    ]


async def get_user_dynamics_with_web_fallback(uid: int) -> tuple[list, bool]:
    fallback_until = dynamic_web_fallback_until.get(uid)
    if fallback_until is not None:
        if fallback_until > monotonic():
            logger.debug(f"动态 gRPC 接口仍在风控，继续使用 Web 接口：{uid}")
            cookies = await get_bilibili_cookies()
            if not cookies:
                raise WebDynamicError(-1, "browser cookies unavailable")
            dynamics = await get_user_dynamics_web(
                uid,
                cookies,
                proxy=plugin_config.bililive_proxy,
                user_agent=plugin_config.bililive_browser_ua or None,
                timeout=plugin_config.bililive_dynamic_timeout,
            )
            return dynamics, True
        del dynamic_web_fallback_until[uid]

    try:
        dynamics = (
            await grpc_get_user_dynamics(
                uid,
                timeout=plugin_config.bililive_dynamic_timeout,
                proxy=plugin_config.bililive_proxy,
            )
        ).list
        dynamic_web_fallback_until.pop(uid, None)
        return list(dynamics), False
    except GrpcError as e:
        if e.code != -352:
            raise
        logger.warning(
            f"动态 gRPC 接口触发风控，切换 Web 接口：{uid} "
            f"{e.code} {e.msg}"
        )
        dynamic_web_fallback_until[uid] = monotonic() + RISK_CONTROL_RETRY_SECONDS
    cookies = await get_bilibili_cookies()
    if not cookies:
        raise WebDynamicError(-1, "browser cookies unavailable")
    dynamics = await get_user_dynamics_web(
        uid,
        cookies,
        proxy=plugin_config.bililive_proxy,
        user_agent=plugin_config.bililive_browser_ua or None,
        timeout=plugin_config.bililive_dynamic_timeout,
    )
    return dynamics, True


async def dy_sched():
    """动态推送"""
    uid = await db.next_uid("dynamic")
    if not uid:
        # 没有订阅先暂停一秒再跳过，不然会导致 CPU 占用过高
        await throttle_dynamic_loop()
        return
    user = await db.get_user(uid=uid)
    if user is None:
        logger.warning(f"动态推送跳过异常订阅 UID：{uid}")
        await throttle_dynamic_loop()
        return
    name = user.name

    retry_at = dynamic_risk_control_until.get(uid)
    if retry_at is not None:
        if retry_at > monotonic():
            logger.debug(f"动态接口风控冷却中，跳过 {name}（{uid}）")
            await throttle_dynamic_loop()
            return
        del dynamic_risk_control_until[uid]

    logger.debug(f"爬取动态 {name}（{uid}）")
    use_web_fallback = False
    try:
        dynamics, use_web_fallback = await get_user_dynamics_with_web_fallback(uid)
    except asyncio.CancelledError:
        logger.debug(f"动态轮询任务已取消：{name}（{uid}）")
        return
    except AioRpcError as e:
        if e.code() == StatusCode.DEADLINE_EXCEEDED:
            logger.error(f"爬取动态超时，将在下个轮询中重试：{e.code()} {e.details()}")
        else:
            logger.error(f"爬取动态失败：{e.code()} {e.details()}")
        await throttle_dynamic_loop()
        return
    except GrpcError as e:
        logger.error(f"爬取动态失败：{e.code} {e.msg}")
        await throttle_dynamic_loop()
        return
    except WebDynamicError as e:
        dynamic_risk_control_until[uid] = monotonic() + RISK_CONTROL_RETRY_SECONDS
        retry_minutes = RISK_CONTROL_RETRY_SECONDS // 60
        logger.warning(
            f"动态 Web 接口获取失败，{name}（{uid}）将在 "
            f"{retry_minutes} 分钟后重试：{e.code} {e.msg}"
        )
        await throttle_dynamic_loop()
        return

    dynamic_risk_control_until.pop(uid, None)

    if not dynamics:  # 没发过动态
        if uid in offset and offset[uid] == -1:  # 不记录会导致第一次发动态不推送
            offset[uid] = 0
        return
    name = get_dynamic_author_name(dynamics[0], use_web_fallback)

    if uid not in offset:  # 已删除
        return
    elif offset[uid] == -1:  # 第一次爬取
        if len(dynamics) == 1:  # 只有一条动态
            offset[uid] = get_dynamic_id(dynamics[0], use_web_fallback)
        else:  # 第一个可能是置顶动态，但置顶也可能是最新一条，所以取前两条的最大值
            offset[uid] = max(
                get_dynamic_id(dynamics[0], use_web_fallback),
                get_dynamic_id(dynamics[1], use_web_fallback),
            )
        return

    dynamic = None
    for dynamic in sorted(
        dynamics,
        key=lambda x: get_dynamic_id(x, use_web_fallback),  # 动态从旧到新排列
    ):
        dynamic_id = get_dynamic_id(dynamic, use_web_fallback)
        dynamic_type = get_dynamic_type(dynamic, use_web_fallback)
        if dynamic_id > offset[uid]:
            logger.info(f"检测到新动态（{dynamic_id}）：{name}（{uid}）")
            image, err = await get_dynamic_screenshot(dynamic_id)
            url = f"https://t.bilibili.com/{dynamic_id}"
            if image is None:
                logger.debug(f"动态不存在，已跳过：{url}")
                return
            elif should_skip_dynamic(dynamic_type, use_web_fallback):
                logger.debug(f"无需推送的动态 {dynamic_type}，已跳过：{url}")
                offset[uid] = dynamic_id
                return
            message = (
                f"{name} {get_dynamic_type_message(dynamic_type, use_web_fallback)}：\n"
                + str(f"动态图片可能截图异常：{err}\n" if err else "")
                + MessageSegment.image(image)
                + f"\n{url}"
            )

            push_list = await db.get_push_list(uid, "dynamic")
            for sets in push_list:
                await safe_send(
                    bot_id=sets.bot_id,
                    send_type=sets.type,
                    type_id=sets.type_id,
                    message=message,
                    at=bool(sets.at) and plugin_config.bililive_dynamic_at,
                )

            offset[uid] = dynamic_id

    if dynamic:
        await db.update_user(uid, name)


def dynamic_lisener(event):
    if hasattr(event, "job_id") and event.job_id != "dynamic_sched":
        return
    job = scheduler.get_job("dynamic_sched")
    if not job:
        scheduler.add_job(
            dy_sched, id="dynamic_sched", next_run_time=datetime.now(scheduler.timezone)
        )


if plugin_config.bililive_dynamic_interval == 0:
    scheduler.add_listener(
        dynamic_lisener,
        EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED | EVENT_SCHEDULER_STARTED,
    )
else:
    scheduler.add_job(
        dy_sched,
        "interval",
        seconds=plugin_config.bililive_dynamic_interval,
        id="dynamic_sched",
    )
