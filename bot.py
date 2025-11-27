import os
import json
import asyncio
from pyrogram import Client, filters
from pytgcalls import PyTgCalls
try:
    from pytgcalls.types.input_stream import AudioPiped
except ModuleNotFoundError:
    print("AudioPiped not found! Install PyTgCalls dev version.")
    AudioPiped = None
from pydub import AudioSegment
from config import *

# ---------------- SILENCE FILE ----------------
silence_file = os.path.join(TEMP_DIR, "silence.mp3")
if not os.path.exists(silence_file):
    silent = AudioSegment.silent(duration=3000)  # 3 seconds
    silent.export(silence_file, format="mp3")

# ---------------- BOT INIT ----------------
bot = Client("vc-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
assistants = []
calls = {}

state_file = os.path.join(BASE_DIR, "sessions.json")
session_files = []

if os.path.exists(state_file):
    with open(state_file, "r") as f:
        session_files = json.load(f)

# ---------------- HELPER ----------------
async def start_assistants():
    global assistants
    for sess in session_files:
        cli = Client(sess, api_id=API_ID, api_hash=API_HASH)
        await cli.start()
        assistants.append(cli)
        calls[cli] = PyTgCalls(cli)
        await calls[cli].start()
    print(f"Loaded {len(assistants)} assistants")

def save_sessions():
    with open(state_file, "w") as f:
        json.dump(session_files, f)

def user_filter(user_ids):
    if isinstance(user_ids, set):
        user_ids = list(user_ids)
    return filters.user(user_ids)

# ---------------- COMMANDS ----------------
@bot.on_message(filters.command("status", PREFIX) & user_filter(sudo_users))
async def status(_, msg):
    await msg.reply(f"Bot alive ✅\nAssistants loaded: {len(assistants)}")

@bot.on_message(filters.command("connect", PREFIX) & user_filter(sudo_users))
async def connect(_, msg):
    if len(msg.command) < 2:
        return await msg.reply("Usage: /connect <string_session>")
    string = msg.command[1]
    sess_path = os.path.join(SESSIONS_DIR, f"session_{len(session_files)+1}.session")
    with open(sess_path, "w") as f:
        f.write(string)
    session_files.append(sess_path)
    save_sessions()
    cli = Client(sess_path, api_id=API_ID, api_hash=API_HASH)
    await cli.start()
    assistants.append(cli)
    calls[cli] = PyTgCalls(cli)
    await calls[cli].start()
    await msg.reply(f"Assistant added: {sess_path}")

@bot.on_message(filters.command("join", PREFIX) & user_filter(sudo_users))
async def join(_, msg):
    if len(msg.command) < 2:
        return await msg.reply("Usage: /join <chat_id>")
    if not AudioPiped:
        return await msg.reply("AudioPiped not available. Install PyTgCalls dev version.")
    chat = msg.command[1]
    for cli in assistants:
        try:
            await cli.join_chat(chat)
            await calls[cli].join_group_call(int(chat), AudioPiped(silence_file))
        except Exception as e:
            print(e)
            continue
    await msg.reply("Joined VC.")

@bot.on_message(filters.command("play", PREFIX) & user_filter(sudo_users))
async def play(_, msg):
    if not AudioPiped:
        return await msg.reply("AudioPiped not available. Install PyTgCalls dev version.")
    if not msg.reply_to_message:
        return await msg.reply("Reply to an audio file with /play")
    file = await msg.reply_to_message.download(os.path.join(TEMP_DIR, "play.mp3"))
    for cli in assistants:
        try:
            await calls[cli].change_stream(0, AudioPiped(file))
        except Exception:
            continue
    await msg.reply("Playing audio...")

# ---------------- MAIN ----------------
async def main():
    await start_assistants()
    await bot.start()
    print("Bot started and ready")
    await asyncio.get_event_loop().create_future()

if __name__ == "__main__":
    asyncio.run(main())