"""
EthioFootball CRBT Bot
A Telegram bot for discovering and activating football CRBT ringtones
via Ethio Telecom's 822 SMS service.
"""

import logging
import os
import time
import asyncio
from functools import wraps
from urllib.parse import quote

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

import db
from config import BOT_TOKEN, ADMIN_IDS, RATE_LIMIT_SECONDS, WEBAPP_URL

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Rate-limit store ──────────────────────────────────────────────────────────
_last_seen: dict = {}

# ── Admin conversation states ─────────────────────────────────────────────────
(
    ADD_TEAM, ADD_TITLE, ADD_CODE, ADD_SMS,
    ADD_FILE, ADD_CAT, ADD_LEAGUE,
    REMOVE_ID,
) = range(8)

# ── Helpers ───────────────────────────────────────────────────────────────────

LEAGUE_EMOJI = {
    "Premier League":           "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "La Liga":                  "🇪🇸",
    "Bundesliga":               "🇩🇪",
    "Serie A":                  "🇮🇹",
    "Ethiopian Premier League": "🇪🇹",
    "Other":                    "🌍",
}


def rate_limit(func):
    @wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        now = time.time()
        if now - _last_seen.get(user_id, 0) < RATE_LIMIT_SECONDS:
            await update.effective_message.reply_text(
                "⏳ Please slow down a bit. Try again in a moment."
            )
            return
        _last_seen[user_id] = now
        return await func(update, ctx, *args, **kwargs)
    return wrapper


def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.id not in ADMIN_IDS:
            await update.effective_message.reply_text("🚫 Admin access required.")
            return ConversationHandler.END
        return await func(update, ctx, *args, **kwargs)
    return wrapper


def build_main_menu():
    leagues = db.get_leagues()
    buttons = []
    row = []
    for i, league in enumerate(leagues):
        emoji = LEAGUE_EMOJI.get(league, "⚽")
        row.append(InlineKeyboardButton(f"{emoji} {league}", callback_data=f"league:{league}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([
        InlineKeyboardButton("🔥 Trending Songs", callback_data="trending"),
        InlineKeyboardButton("🔍 Search",          callback_data="search_hint"),
    ])
    buttons.append([
        InlineKeyboardButton("ℹ️ How CRBT Works", callback_data="howto"),
    ])
    return InlineKeyboardMarkup(buttons)


def build_teams_menu(league: str):
    teams = db.get_teams_by_league(league)
    buttons = []
    row = []
    for i, team in enumerate(teams):
        row.append(InlineKeyboardButton(f"⚽ {team}", callback_data=f"team:{league}:{team}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def build_songs_menu(team: str, league: str):
    songs = db.get_songs_by_team(team)
    buttons = [
        [InlineKeyboardButton(f"🎵 {s['song_title']}", callback_data=f"song:{s['id']}")]
        for s in songs
    ]
    buttons.append([InlineKeyboardButton(f"🔙 Back to {league}", callback_data=f"league:{league}")])
    return InlineKeyboardMarkup(buttons)


def build_song_detail_menu(song_id: int, league: str, team: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Play Preview",                   callback_data=f"preview:{song_id}")],
        [InlineKeyboardButton("📲 Set as My Ringtone (Activate)",  callback_data=f"activate:{song_id}")],
        [InlineKeyboardButton(f"🔙 Back to {team}",                callback_data=f"team:{league}:{team}")],
    ])


def song_detail_text(song: dict) -> str:
    return (
        f"⚽ <b>{song['team_name']}</b>\n"
        f"🎵 <b>{song['song_title']}</b>\n"
        f"🏷 CRBT Code: <code>{song['crbt_code']}</code>\n\n"
        f"📱 <b>Activation Instructions:</b>\n"
        f"Send an SMS to <b>822</b>\n\n"
        f"Message:\n"
        f"<code>{song['sms_command']}</code>\n\n"
        f"<i>First time? Activate CRBT service first:\n"
        f"Send <code>A</code> to <b>822</b></i>"
    )


# ── /start ────────────────────────────────────────────────────────────────────

@rate_limit
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"🇪🇹⚽ <b>Welcome to EthioFootball CRBT Bot</b>, {user.first_name}!\n\n"
        "Discover your favourite football team's CRBT songs and activate them "
        "on <b>Ethio Telecom</b> in seconds.\n\n"
        "👇 Choose a league or browse trending songs:"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=build_main_menu())


# ── /help ─────────────────────────────────────────────────────────────────────

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "🆘 <b>EthioFootball CRBT Bot — Help</b>\n\n"
        "<b>Commands:</b>\n"
        "/start — Main menu\n"
        "/search &lt;query&gt; — Search for a song or team\n"
        "/help — This message\n\n"
        "<b>How it works:</b>\n"
        "1. Browse leagues → teams → songs\n"
        "2. Listen to a 15–30 sec preview\n"
        "3. Tap <i>Activate CRBT</i> and follow the SMS instructions\n"
        "4. Your Ethio Telecom number gets the ringtone! 🎶\n\n"
        "<b>First-time CRBT activation:</b>\n"
        "Send <code>A</code> to <b>822</b> before subscribing."
    )
    await update.message.reply_text(text, parse_mode="HTML")


# ── /search ───────────────────────────────────────────────────────────────────

@rate_limit
async def cmd_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = " ".join(ctx.args).strip()
    if not query:
        await update.message.reply_text(
            "🔍 Usage: /search &lt;team or song name&gt;\nExample: /search Arsenal",
            parse_mode="HTML",
        )
        return

    if len(query) > 50:
        await update.message.reply_text("❌ Query too long. Max 50 characters.")
        return

    results = db.search_songs(query)
    if not results:
        await update.message.reply_text(
            f"😕 No results found for <b>{query}</b>.", parse_mode="HTML"
        )
        return

    buttons = [
        [InlineKeyboardButton(
            f"⚽ {s['team_name']} — 🎵 {s['song_title']}",
            callback_data=f"song:{s['id']}"
        )]
        for s in results[:10]
    ]
    buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])

    await update.message.reply_text(
        f"🔍 Found <b>{len(results)}</b> result(s) for <b>{query}</b>:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ── Callback query router ─────────────────────────────────────────────────────

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "main_menu":
        await query.edit_message_text(
            "🇪🇹⚽ <b>EthioFootball CRBT Bot</b>\n\nChoose a league:",
            parse_mode="HTML",
            reply_markup=build_main_menu(),
        )

    elif data.startswith("league:"):
        league = data.split(":", 1)[1]
        emoji = LEAGUE_EMOJI.get(league, "⚽")
        await query.edit_message_text(
            f"{emoji} <b>{league}</b>\n\nSelect a team:",
            parse_mode="HTML",
            reply_markup=build_teams_menu(league),
        )

    elif data.startswith("team:"):
        _, league, team = data.split(":", 2)
        await query.edit_message_text(
            f"⚽ <b>{team}</b>\n\n🎵 Available CRBT songs:",
            parse_mode="HTML",
            reply_markup=build_songs_menu(team, league),
        )

    elif data.startswith("song:"):
        song_id = int(data.split(":")[1])
        song = db.get_song_by_id(song_id)
        if not song:
            await query.edit_message_text("❌ Song not found.")
            return
        await query.edit_message_text(
            song_detail_text(song),
            parse_mode="HTML",
            reply_markup=build_song_detail_menu(song_id, song["league"], song["team_name"]),
        )

    elif data.startswith("preview:"):
        song_id = int(data.split(":")[1])
        song = db.get_song_by_id(song_id)
        if not song:
            await query.message.reply_text("❌ Song not found.")
            return
        preview_path = song["preview_file"]
        if not os.path.exists(preview_path):
            await query.message.reply_text(
                f"⚠️ Preview file not available yet for <b>{song['song_title']}</b>.\n"
                "Please add the MP3 file to the /previews folder.",
                parse_mode="HTML",
            )
            return
        await query.message.reply_text(
            f"▶️ Playing preview: <b>{song['song_title']}</b>", parse_mode="HTML"
        )
        with open(preview_path, "rb") as audio_file:
            await query.message.reply_audio(
                audio=audio_file,
                title=song["song_title"],
                performer=song["team_name"],
                caption=(
                    f"🎵 {song['song_title']} — {song['team_name']}\n"
                    f"🏷 Code: {song['crbt_code']}"
                ),
            )

    elif data.startswith("activate:"):
        song_id = int(data.split(":")[1])
        song = db.get_song_by_id(song_id)
        if not song:
            await query.message.reply_text("❌ Song not found.")
            return

        from urllib.parse import urlencode
        params = urlencode({
            "team":  song["team_name"],
            "title": song["song_title"],
            "code":  song["crbt_code"],
            "sms":   song["sms_command"],
        })

        text = (
            f"📲 <b>Set as My Ringtone</b>\n\n"
            f"⚽ <b>{song['team_name']}</b>\n"
            f"🎵 <b>{song['song_title']}</b>\n"
            f"🏷 Code: <code>{song['crbt_code']}</code>\n\n"
            f"Tap the button below to activate.\n"
            f"The page opens in your browser — tap the button\n"
            f"and your SMS app opens with everything pre-filled.\n"
            f"Just tap <b>Send</b> ✅"
        )

        if WEBAPP_URL and WEBAPP_URL not in ("YOUR_WEBAPP_URL_HERE", ""):
            webapp_url = f"{WEBAPP_URL}?{params}"
            activate_btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("📲 Activate CRBT — Open Page", url=webapp_url)],
            ])
        else:
            activate_btn = None

        await query.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=activate_btn,
        )

        if not activate_btn:
            fallback = (
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🔵 <b>STEP 1 — First Time Only</b>\n"
                f"📱 To: <b>822</b>  ✉️ Message: <code>A</code>\n\n"
                f"🟢 <b>STEP 2 — Subscribe</b>\n"
                f"📱 To: <b>822</b>  ✉️ Message: <code>{song['sms_command']}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            await query.message.reply_text(fallback, parse_mode="HTML")

    elif data.startswith("copy:"):
        song_id = int(data.split(":")[1])
        song = db.get_song_by_id(song_id)
        if not song:
            await query.message.reply_text("❌ Song not found.")
            return
        await query.message.reply_text(
            f"📋 <b>SMS Command (tap to copy):</b>\n\n"
            f"<code>{song['sms_command']}</code>\n\n"
            f"Send to: <b>822</b>",
            parse_mode="HTML",
        )

    elif data == "trending":
        songs = db.get_trending_songs(6)
        buttons = [
            [InlineKeyboardButton(
                f"⚽ {s['team_name']} — 🎵 {s['song_title']}",
                callback_data=f"song:{s['id']}"
            )]
            for s in songs
        ]
        buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
        await query.edit_message_text(
            "🔥 <b>Trending CRBT Songs</b>\n\nTop picks right now:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif data == "search_hint":
        await query.message.reply_text(
            "🔍 Use the /search command:\n\nExample: /search Arsenal"
        )

    elif data == "howto":
        text = (
            "ℹ️ <b>How CRBT Works on Ethio Telecom</b>\n\n"
            "<b>What is CRBT?</b>\n"
            "Caller Ring Back Tone — instead of a normal ring, your callers "
            "hear your chosen football song! 🎶\n\n"
            "<b>Activation steps:</b>\n"
            "1️⃣ First time: Send <code>A</code> to <b>822</b>\n"
            "2️⃣ Choose a song in this bot\n"
            "3️⃣ Send the SMS command (e.g. <code>SUB MU124</code>) to <b>822</b>\n"
            "4️⃣ Done! Your callers hear your song 🏆\n\n"
            "<b>To stop:</b>\n"
            "Send <code>STOP</code> to <b>822</b>\n\n"
            "<i>Ethio Telecom subscribers only. Standard SMS charges apply.</i>"
        )
        await query.message.reply_text(text, parse_mode="HTML")


# ── Admin: /addsong ───────────────────────────────────────────────────────────

@admin_only
async def addsong_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("➕ <b>Add New Song</b>\n\nEnter team name:", parse_mode="HTML")
    return ADD_TEAM

async def addsong_team(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_song"] = {"team_name": update.message.text.strip()}
    await update.message.reply_text("Enter song title:")
    return ADD_TITLE

async def addsong_title(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_song"]["song_title"] = update.message.text.strip()
    await update.message.reply_text("Enter CRBT code (e.g. MU124):")
    return ADD_CODE

async def addsong_code(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_song"]["crbt_code"] = update.message.text.strip().upper()
    await update.message.reply_text("Enter SMS command (e.g. SUB MU124):")
    return ADD_SMS

async def addsong_sms(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_song"]["sms_command"] = update.message.text.strip().upper()
    await update.message.reply_text("Enter preview file path (e.g. previews/manu.mp3):")
    return ADD_FILE

async def addsong_file(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_song"]["preview_file"] = update.message.text.strip()
    await update.message.reply_text("Enter category (e.g. Anthem / National):")
    return ADD_CAT

async def addsong_cat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_song"]["category"] = update.message.text.strip()
    await update.message.reply_text(
        "Enter league (e.g. Premier League / La Liga / Ethiopian Premier League):"
    )
    return ADD_LEAGUE

async def addsong_league(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    s = ctx.user_data["new_song"]
    s["league"] = update.message.text.strip()
    ok = db.add_song(
        s["team_name"], s["song_title"], s["crbt_code"],
        s["sms_command"], s["preview_file"], s["category"], s["league"]
    )
    if ok:
        await update.message.reply_text(
            f"✅ Song <b>{s['song_title']}</b> added successfully!", parse_mode="HTML"
        )
    else:
        await update.message.reply_text("❌ CRBT code already exists. Song not added.")
    ctx.user_data.clear()
    return ConversationHandler.END

async def addsong_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END


# ── Admin: /removesong ────────────────────────────────────────────────────────

@admin_only
async def removesong_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    songs = db.get_all_songs()
    if not songs:
        await update.message.reply_text("No songs in database.")
        return ConversationHandler.END
    lines = [f"ID {s['id']}: {s['team_name']} — {s['song_title']}" for s in songs]
    await update.message.reply_text(
        "🗑 <b>Remove Song</b>\n\n" + "\n".join(lines) + "\n\nSend the song ID to remove:",
        parse_mode="HTML",
    )
    return REMOVE_ID

async def removesong_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("❌ Invalid ID. Send a number.")
        return REMOVE_ID
    ok = db.remove_song(int(text))
    if ok:
        await update.message.reply_text(f"✅ Song ID {text} removed.")
    else:
        await update.message.reply_text("❌ Song not found.")
    return ConversationHandler.END


# ── Admin: /listsongs ─────────────────────────────────────────────────────────

@admin_only
async def cmd_listsongs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    songs = db.get_all_songs()
    if not songs:
        await update.message.reply_text("No songs in database.")
        return
    lines = [
        f"<b>{s['id']}.</b> {s['team_name']} — {s['song_title']} "
        f"[<code>{s['crbt_code']}</code>] ({s['league']})"
        for s in songs
    ]
    chunk, chunks = "", []
    for line in lines:
        if len(chunk) + len(line) > 3800:
            chunks.append(chunk)
            chunk = ""
        chunk += line + "\n"
    if chunk:
        chunks.append(chunk)
    for part in chunks:
        await update.message.reply_text(
            f"🎵 <b>All Songs ({len(songs)}):</b>\n\n" + part,
            parse_mode="HTML",
        )


# ── Unknown command ───────────────────────────────────────────────────────────

async def unknown_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Unknown command. Use /start to open the main menu or /help for assistance."
    )


# ── Main ──────────────────────────────────────────────────────────────────────

async def run_bot():
    db.init_db()
    logger.info("Database initialised.")

    app = Application.builder().token(BOT_TOKEN).build()

    addsong_conv = ConversationHandler(
        entry_points=[CommandHandler("addsong", addsong_start)],
        states={
            ADD_TEAM:   [MessageHandler(filters.TEXT & ~filters.COMMAND, addsong_team)],
            ADD_TITLE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, addsong_title)],
            ADD_CODE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, addsong_code)],
            ADD_SMS:    [MessageHandler(filters.TEXT & ~filters.COMMAND, addsong_sms)],
            ADD_FILE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, addsong_file)],
            ADD_CAT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, addsong_cat)],
            ADD_LEAGUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, addsong_league)],
        },
        fallbacks=[CommandHandler("cancel", addsong_cancel)],
    )

    removesong_conv = ConversationHandler(
        entry_points=[CommandHandler("removesong", removesong_start)],
        states={
            REMOVE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, removesong_id)],
        },
        fallbacks=[CommandHandler("cancel", addsong_cancel)],
    )

    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("help",      cmd_help))
    app.add_handler(CommandHandler("search",    cmd_search))
    app.add_handler(CommandHandler("listsongs", cmd_listsongs))
    app.add_handler(addsong_conv)
    app.add_handler(removesong_conv)
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("🇪🇹⚽ EthioFootball CRBT Bot is running…")

    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        # Run forever until interrupted
        await asyncio.Event().wait()
        await app.updater.stop()
        await app.stop()


if __name__ == "__main__":
    asyncio.run(run_bot())
