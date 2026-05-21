# 🇪🇹⚽ EthioFootball CRBT Bot

A Telegram bot that helps Ethiopian Ethio Telecom users discover, preview, and activate football CRBT (Caller Ring Back Tone) songs via SMS to **822**.

---

## 🎯 Features

- Browse songs by **league → team → song**
- 🔥 Trending songs section
- 🔍 Search by team or song name
- ▶️ **Audio preview** (15–30 sec MP3 sent inside Telegram)
- 🚀 One-tap SMS activation link (`sms:822?body=SUB CODE`)
- 📋 Copy SMS command
- ℹ️ First-time CRBT service activation guide
- 🔐 Admin panel: add / remove / list songs
- ⏳ Per-user rate limiting

---

## 📂 Project Structure

```
ethiofootball_crbt_bot/
├── main.py           ← Bot logic
├── db.py             ← SQLite helpers
├── config.py         ← Env var loader
├── songs.db          ← Auto-created on first run
├── requirements.txt
├── .env.example      ← Copy to .env and fill in
│
├── previews/         ← Drop your MP3 preview files here
│   ├── manu.mp3
│   ├── arsenal.mp3
│   └── ...
│
└── data/
    └── songs.json    ← Seed data (auto-loaded on first run)
```

---

## 🚀 Quick Start (Local)

### 1. Clone / unzip the project

```bash
cd ethiofootball_crbt_bot
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_IDS=your_telegram_user_id
```

> **Get BOT_TOKEN:** Message [@BotFather](https://t.me/BotFather) → `/newbot`  
> **Get your user ID:** Message [@userinfobot](https://t.me/userinfobot)

### 5. Add preview MP3 files

Place 15–30 second MP3 clips in the `previews/` folder.  
File names must match the `preview_file` field in `data/songs.json`.

Example:
```
previews/manu.mp3
previews/arsenal.mp3
previews/madrid.mp3
```

### 6. Run the bot

```bash
python main.py
```

---

## ☁️ Free Cloud Deployment

### Option A — Render.com (Recommended)

1. Push project to a **GitHub repo**
2. Go to [render.com](https://render.com) → New → **Web Service**
3. Connect your GitHub repo
4. Settings:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
5. Add environment variables under **Environment**:
   - `BOT_TOKEN`
   - `ADMIN_IDS`
6. Click **Deploy**

> ⚠️ Free Render instances sleep after 15 min of inactivity.  
> For a Telegram bot (polling), this is fine — it restarts on the next message.

### Option B — Railway.app

1. Push to GitHub
2. [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Add environment variables in the **Variables** tab
4. Start command: `python main.py`

---

## 🗄️ Database

SQLite database `songs.db` is created automatically on first run and seeded from `data/songs.json`.

### Schema

| Field         | Type    | Description                        |
|---------------|---------|------------------------------------|
| id            | INTEGER | Auto primary key                   |
| team_name     | TEXT    | e.g. Manchester United             |
| song_title    | TEXT    | e.g. Glory Glory Man United        |
| crbt_code     | TEXT    | Unique, e.g. MU124                 |
| sms_command   | TEXT    | e.g. SUB MU124                     |
| preview_file  | TEXT    | Path to MP3, e.g. previews/manu.mp3|
| category      | TEXT    | e.g. Anthem, National              |
| league        | TEXT    | e.g. Premier League                |

---

## 🤖 Bot Commands

| Command         | Who      | Description                    |
|-----------------|----------|--------------------------------|
| `/start`        | All      | Main menu                      |
| `/help`         | All      | Help & instructions            |
| `/search query` | All      | Search songs/teams             |
| `/addsong`      | Admin    | Add a new song (step-by-step)  |
| `/removesong`   | Admin    | Remove a song by ID            |
| `/listsongs`    | Admin    | List all songs                 |
| `/cancel`       | Admin    | Cancel ongoing admin action    |

---

## 📱 CRBT Activation Flow

```
User opens bot
    ↓
Selects league → team → song
    ↓
Plays 15–30 sec preview (MP3 in Telegram)
    ↓
Taps "🚀 Activate CRBT"
    ↓
Bot shows SMS instructions + deep link
    ↓
User taps link → SMS app opens with:
  To: 822
  Message: SUB MU124
    ↓
User taps SEND
    ↓
Ethio Telecom activates CRBT ✅
```

**First-time users** must first send `A` to `822` to enable the CRBT service.

---

## 🔐 Security

- Bot token stored in `.env` (never committed to git)
- Admin commands protected by Telegram user ID whitelist
- Input validation on all user inputs
- Per-user rate limiting (configurable, default 3 seconds)

---

## 📦 Dependencies

| Package               | Version  | Purpose            |
|-----------------------|----------|--------------------|
| python-telegram-bot   | 21.5     | Telegram Bot API   |
| python-dotenv         | 1.0.1    | Env var management |

SQLite3 is built into Python — no extra install needed.

---

## 🛠 Extending the Bot

- **Add songs:** Use `/addsong` as admin or edit `data/songs.json` and re-run
- **Add leagues:** Just add songs with a new `league` value — menus update automatically
- **Add preview files:** Drop MP3s in `previews/` and reference them in the database
- **Webhook mode:** For production, switch `run_polling()` to `run_webhook()` in `main.py`

---

## 📄 License

MIT — Free to use and modify for personal and commercial projects.
