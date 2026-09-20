from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from linger import script

log = logging.getLogger("linger")

HTML = ParseMode.HTML


@dataclass
class DemoState:
    step: int = 0
    presenter_id: int | None = None
    poll_message: Message | None = None
    vote: str | None = None
    feedback: dict[str, dict[str, str]] = field(default_factory=dict)
    feedback_message: Message | None = None


_states: dict[int, DemoState] = {}


def state_for(chat_id: int) -> DemoState:
    return _states.setdefault(chat_id, DemoState())


def _remember_presenter(st: DemoState, update: Update) -> None:
    user = update.effective_user
    if user is not None:
        st.presenter_id = user.id


def kb(*rows: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    buttons = []
    for row in rows:
        buttons.append(
            [
                InlineKeyboardButton(label, url=data) if data.startswith("http") else InlineKeyboardButton(label, callback_data=data)
                for label, data in row
            ]
        )
    return InlineKeyboardMarkup(buttons)


def typing_delay(text: str) -> float:
    return min(4.0, max(1.0, len(text) / 50))


async def say(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, *, bot: Bot | None = None, **kwargs) -> Message:
    bot = bot or context.bot
    await bot.send_chat_action(chat_id, ChatAction.TYPING)
    await asyncio.sleep(typing_delay(text))
    return await bot.send_message(chat_id, text, parse_mode=HTML, **kwargs)


async def member_say(context: ContextTypes.DEFAULT_TYPE, chat_id: int, name: str, text: str) -> Message:
    bot = context.bot_data.get("members", {}).get(name)
    if bot is None:
        return await say(context, chat_id, f"<b>{name}</b>\n{text}")
    return await say(context, chat_id, text, bot=bot)


async def progress(context: ContextTypes.DEFAULT_TYPE, chat_id: int, steps: list[str], delay: float = 1.5) -> Message:
    msg = await say(context, chat_id, steps[0])
    for text in steps[1:]:
        await asyncio.sleep(delay)
        await msg.edit_text(text, parse_mode=HTML)
    return msg


def build_ics() -> bytes:
    d = script.hangout_date()
    local = "%Y%m%dT%H%M%S"
    start = datetime(d.year, d.month, d.day, *script.EVENT_START)
    end = datetime(d.year, d.month, d.day, *script.EVENT_END)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Linger//Hangout Planner//EN",
        "BEGIN:VEVENT",
        f"UID:linger-{d.isoformat()}@linger.demo",
        f"DTSTAMP:{stamp}",
        f"DTSTART;TZID={script.TZ.key}:{start.strftime(local)}",
        f"DTEND;TZID={script.TZ.key}:{end.strftime(local)}",
        f"SUMMARY:{script.EVENT_TITLE}",
        f"LOCATION:{script.EVENT_LOCATION}",
        "DESCRIPTION:Art market at Civic Center Plaza\\, then Green Bowl at 4:30 PM. Planned by Linger.",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines).encode()


# --- beats -------------------------------------------------------------------


async def beat_chatter(context, chat_id: int, st: DemoState) -> None:
    for name, text in script.GROUP_CHATTER:
        await member_say(context, chat_id, name, text)
    st.step = 1


async def beat_constraints(context, chat_id: int, st: DemoState) -> None:
    await progress(context, chat_id, [script.CHECKING, script.CHECKED], delay=2.5)
    await say(
        context,
        chat_id,
        script.CONSTRAINTS,
        reply_markup=kb([("Looks right", "looks_right"), ("Edit", "edit")]),
    )
    st.step = 2


def render_plan(p: dict) -> str:
    signals = "\n".join(p["signals"])
    return (
        f"<b>Plan {p['key']} · {p['title']}</b>  <code>{p['fit']} fit</code>\n"
        f"{p['meta']}\n"
        f"<i>{p['arrivals']}</i>\n"
        f"{signals}\n"
        f"<b>Plan B</b>  {p['plan_b']}"
    )


async def beat_plans(context, chat_id: int, st: DemoState) -> None:
    await say(context, chat_id, script.PLANS_INTRO)
    for p in script.PLANS:
        await say(context, chat_id, render_plan(p))
    await asyncio.sleep(2)
    await beat_poll(context, chat_id, st)


def render_poll(st: DemoState) -> str:
    lines = [f"<b>{script.POLL_TITLE}</b>", ""]
    if st.vote is None:
        for _, label in script.POLL_OPTIONS:
            lines.append(f"○ {label}")
        lines += ["", "<i>0 votes</i>"]
        return "\n".join(lines)

    voters: dict[str, list[str]] = {k: list(v) for k, v in script.POLL_OTHERS.items()}
    voters.setdefault(st.vote, []).append(script.PRESENTER)
    total = sum(len(v) for v in voters.values())
    for key, label in script.POLL_OPTIONS:
        names = voters.get(key, [])
        pct = round(100 * len(names) / total) if total else 0
        mark = "●" if key == st.vote else "○"
        bar = "▰" * len(names) + "▱" * (total - len(names))
        who = f"  <i>{', '.join(names)}</i>" if names else ""
        lines.append(f"{mark} {label}\n    {bar} {pct}%{who}")
    lines += ["", f"<i>{total} votes · Final results</i>"]
    return "\n".join(lines)


async def beat_poll(context, chat_id: int, st: DemoState) -> None:
    summary = "\n".join(
        f"{'🎲🎨☕'[i]} Plan {p['key']} · {p['title']} · ~{p['meta'].split('~')[1]}"
        for i, p in enumerate(script.PLANS)
    )
    await say(context, chat_id, summary)
    st.vote = None
    st.poll_message = await say(
        context,
        chat_id,
        render_poll(st),
        reply_markup=kb(*([(label, f"vote:{key}")] for key, label in script.POLL_OPTIONS)),
    )
    st.step = 3


async def beat_votes(context, chat_id: int, st: DemoState, vote: str = "2") -> None:
    st.vote = vote
    if st.poll_message is not None:
        try:
            await st.poll_message.edit_text(render_poll(st), parse_mode=HTML)
        except TelegramError:
            log.exception("poll edit failed")
    await asyncio.sleep(1.5)
    await member_say(context, chat_id, "Andrew", script.ANDREW_VOTE_MSG)
    await asyncio.sleep(3)
    await beat_result(context, chat_id, st)


async def beat_result(context, chat_id: int, st: DemoState) -> None:
    await say(context, chat_id, script.RESULT_INTRO)
    await progress(context, chat_id, script.BOOKING_STEPS, delay=1.8)
    await say(
        context,
        chat_id,
        script.RESULT_CARD.format(date=script.hangout_date_label()),
        reply_markup=kb(
            [("🚲 Bike route", script.MAPS_BIKE_URL), ("🅿️ Garage A", script.MAPS_GARAGE_URL)],
            [("Change something", "change")],
        ),
    )
    await context.bot.send_document(
        chat_id,
        document=build_ics(),
        filename=f"{script.EVENT_TITLE}.ics",
        caption="📅 Add to your calendar",
    )
    await asyncio.sleep(3)
    await beat_dm(context, chat_id, st)


async def beat_dm(context, chat_id: int, st: DemoState) -> None:
    if st.presenter_id is None:
        await say(context, chat_id, "⚠️ I don't know who to DM yet — send /next from your own account.")
        st.step = 4
        return
    try:
        await say(context, st.presenter_id, script.DM_INTRO)
        await say(
            context,
            st.presenter_id,
            script.DM_CARD,
            reply_markup=kb([("🚲 Open bike route", script.MAPS_BIKE_URL)]),
        )
        await say(context, st.presenter_id, script.DM_OUTRO)
    except TelegramError:
        await say(
            context,
            chat_id,
            "⚠️ Couldn't DM you. Open a private chat with me and send /start.",
        )
    st.step = 4


async def beat_live_update(context, chat_id: int, st: DemoState) -> None:
    await say(
        context,
        chat_id,
        script.LIVE_UPDATE,
        reply_markup=kb([("Yes, update everyone", "live:yes"), ("Keep original", "live:no")]),
    )
    st.step = 5


def render_feedback(st: DemoState) -> str:
    lines = [script.FEEDBACK_INTRO, ""]
    for key, label in script.FEEDBACK_STOPS:
        votes = st.feedback.get(key, {})
        marks = "  ".join(f"{'👍' if v == 'up' else '👎'} {name}" for name, v in votes.items())
        lines.append(f"• {label}" + (f"\n    {marks}" if marks else ""))
    return "\n".join(lines)


def feedback_kb(st: DemoState) -> InlineKeyboardMarkup:
    rows = []
    for key, label in script.FEEDBACK_STOPS:
        if script.PRESENTER in st.feedback.get(key, {}):
            continue
        rows.append([(f"👍 {label}", f"fb:{key}:up"), (f"👎 {label}", f"fb:{key}:down")])
    return kb(*rows)


async def _refresh_feedback(st: DemoState) -> None:
    if st.feedback_message is None:
        return
    try:
        await st.feedback_message.edit_text(render_feedback(st), parse_mode=HTML, reply_markup=feedback_kb(st))
    except TelegramError:
        log.exception("feedback edit failed")


async def _andrew_feedback(context, chat_id: int, st: DemoState) -> None:
    await asyncio.sleep(6)
    if _states.get(chat_id) is not st:
        return
    for key, value in script.ANDREW_FEEDBACK:
        st.feedback.setdefault(key, {})["Andrew"] = value
        await _refresh_feedback(st)
        await asyncio.sleep(1.5)
    if _states.get(chat_id) is st:
        await say(context, chat_id, script.FEEDBACK_LEARNED)


async def beat_applied(context, chat_id: int, st: DemoState) -> None:
    await progress(context, chat_id, script.LIVE_STEPS, delay=1.8)
    st.step = 6


async def beat_feedback(context, chat_id: int, st: DemoState) -> None:
    st.feedback = {}
    st.feedback_message = await say(context, chat_id, render_feedback(st), reply_markup=feedback_kb(st))
    st.step = 7
    asyncio.create_task(_andrew_feedback(context, chat_id, st))


BEATS = [
    beat_chatter,
    beat_constraints,
    beat_plans,
    beat_votes,
    beat_live_update,
    beat_applied,
    beat_feedback,
]


async def advance(context, chat_id: int, st: DemoState) -> None:
    if st.step >= len(BEATS):
        await say(context, chat_id, "That's the end of the demo. /reset to start over.")
        return
    await BEATS[st.step](context, chat_id, st)


# --- handlers ----------------------------------------------------------------


async def _delete_quietly(message: Message | None) -> None:
    if message is None:
        return
    try:
        await message.delete()
    except TelegramError:
        log.warning("could not delete presenter command (bot needs 'Delete messages' admin right)")


async def cmd_next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    st = state_for(chat_id)
    _remember_presenter(st, update)
    await _delete_quietly(update.message)
    await advance(context, chat_id, st)


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    _states.pop(chat_id, None)
    await _delete_quietly(update.message)
    await context.bot.send_message(chat_id, script.RESET_DONE)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"Hi, I'm {script.BOT_NAME}. Add me to a group and @mention me to plan a hangout."
    )


async def on_mention(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if msg is None or msg.text is None:
        return
    if f"@{context.bot.username}".lower() not in msg.text.lower():
        return
    chat_id = update.effective_chat.id
    st = state_for(chat_id)
    _remember_presenter(st, update)
    if st.step > 1:
        return
    await beat_constraints(context, chat_id, st)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    st = state_for(chat_id)
    _remember_presenter(st, update)
    data = q.data or ""

    if data == "looks_right":
        await q.edit_message_reply_markup(None)
        if st.step == 2:
            await beat_plans(context, chat_id, st)
    elif data == "edit":
        await say(context, chat_id, script.ACKS["edit"])
    elif data.startswith("vote:"):
        if st.step == 3:
            await q.edit_message_reply_markup(None)
            await beat_votes(context, chat_id, st, vote=data.split(":", 1)[1])
    elif data == "change":
        await say(context, chat_id, script.ACKS["change"])
    elif data == "live:yes":
        await q.edit_message_reply_markup(None)
        if st.step == 5:
            await beat_applied(context, chat_id, st)
    elif data == "live:no":
        await q.edit_message_reply_markup(None)
        await say(context, chat_id, script.LIVE_KEPT)
    elif data.startswith("fb:"):
        _, key, value = data.split(":")
        st.feedback.setdefault(key, {})[script.PRESENTER] = value
        await _refresh_feedback(st)


async def _init_members(app: Application) -> None:
    members: dict[str, Bot] = {}
    for name, env_var in script.MEMBER_BOTS.items():
        token = os.environ.get(env_var)
        if not token:
            log.warning("%s not set; %s will be posted by the main bot with a name prefix", env_var, name)
            continue
        bot = Bot(token)
        await bot.initialize()
        members[name] = bot
        log.info("member bot %s -> @%s", name, bot.username)
    app.bot_data["members"] = members


async def _shutdown_members(app: Application) -> None:
    for bot in app.bot_data.get("members", {}).values():
        await bot.shutdown()


def build_app(token: str) -> Application:
    app = Application.builder().token(token).post_init(_init_members).post_shutdown(_shutdown_members).build()
    app.add_handler(CommandHandler("start", cmd_start, filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("next", cmd_next))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & filters.Entity("mention"), on_mention))
    return app
