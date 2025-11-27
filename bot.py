import os
import json
import asyncio
from pyrogram import Client, filters
from pytgcalls import PyTgCalls
try:
    from pytgcalls.types.input_stream import AudioPiped
except ModuleNotFoundError:
    print("AudioPiped not found! Make sure pytgcalls dev version is installed.")
    AudioPiped = None
from pydub import AudioSegment
from config import *

# -------------------- CREATE SILENCE FILE --------------------
silence_file = os.path.join(TEMP_DIR, "silence.mp3")
if not os.path.exists(silence_file):
    print("Creating silence.mp3...")
    silent = AudioSegment.silent(duration=3000)  # 3 seconds
    silent.export(silence_file, format="mp3")

# -------------------- INITIALIZE BOT --------------------
bot = Client("vc-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

assistants = []
calls = {}
recording = False
silenced = False
paused_streams = {}

state_file = "sessions.json"
session_files = []

if os.path.exists(state_file):
    with open(state_file, "r") as f:
        session_files = json.load(f)

# Ensure sudo_users is a list
sudo_users = list(sudo_users)

# -------------------- HELPER FUNCTIONS --------------------
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

# -------------------- COMMANDS --------------------
def user_filter(user_ids):
    """Return filters.user() compatible with Pyrogram (list or int)."""
    if isinstance(user_ids, set):
        return filters.user(list(user_ids))
    return filters.user(user_ids)

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

    await msg.reply(f"Added assistant: {sess_path}")

@bot.on_message(filters.command("disconnect", PREFIX) & user_filter(sudo_users))
async def disconnect(_, msg):
    if len(msg.command) < 2:
        return await msg.reply("Usage: /disconnect <session_number>")
    try:
        idx = int(msg.command[1]) - 1
        cli = assistants.pop(idx)
        await calls[cli].stop()
        os.remove(session_files.pop(idx))
        save_sessions()
        await msg.reply("Assistant removed successfully!")
    except Exception:
        await msg.reply("Invalid session number.")

@bot.on_message(filters.command("join", PREFIX) & user_filter(sudo_users))
async def join(_, msg):
    if len(msg.command) < 2:
        return await msg.reply("Usage: /join <chat_link_or_id>")
    if not AudioPiped:
        return await msg.reply("AudioPiped not available. Install pytgcalls dev version.")

    chat = msg.command[1]
    for cli in assistants:
        try:
            await cli.join_chat(chat)
            await calls[cli].join_group_call(int(chat), AudioPiped(silence_file))
        except Exception:
            continue
    await msg.reply("Joined VC.")

@bot.on_message(filters.command("leave", PREFIX) & user_filter(sudo_users))
async def leave(_, msg):
    chat = msg.command[1] if len(msg.command) > 1 else None
    for cli in assistants:
        try:
            await calls[cli].leave_group_call(int(chat))
        except Exception:
            continue
    await msg.reply("Left VC.")

@bot.on_message(filters.command("record", PREFIX) & user_filter(sudo_users))
async def start_record(_, msg):
    global recording
    recording = True
    await msg.reply("Recording started.")

@bot.on_message(filters.command("stoprecord", PREFIX) & user_filter(sudo_users))
async def stop_record(_, msg):
    global recording
    recording = False
    await msg.reply("Recording stopped.")

# -------------------- SUDO MANAGEMENT --------------------
@bot.on_message(filters.command("addsudo", PREFIX) & user_filter(OWNER_ID))
async def addsudo(_, msg):
    if len(msg.command) < 2:
        return await msg.reply("Usage: /addsudo <user_id>")
    uid = int(msg.command[1])
    if uid not in sudo_users:
        sudo_users.append(uid)
    await msg.reply(f"User {uid} added as sudo.")

@bot.on_message(filters.command("delsudo", PREFIX) & user_filter(OWNER_ID))
async def delsudo(_, msg):
    if len(msg.command) < 2:
        return await msg.reply("Usage: /delsudo <user_id>")
    uid = int(msg.command[1])
    if uid in sudo_users:
        sudo_users.remove(uid)
    await msg.reply(f"User {uid} removed from sudo.")

# -------------------- STATUS & HELP --------------------
@bot.on_message(filters.command("status", PREFIX) & user_filter(sudo_users))
async def status(_, msg):
    text = f"""
📊 Bot Status
Assistants: {len(assistants)}
Sudo Users: {sudo_users}
Recording: {recording}
Silenced: {silenced}
"""
    await msg.reply(text)

@bot.on_message(filters.command("help", PREFIX) & user_filter(sudo_users + [OWNER_ID]))
async def help_cmd(_, msg):
    help_text = """
🔰 VC Multi-Assistant Bot — Help Menu

**Assistant Control**
• /connect <string_session>
• /disconnect <session_no>
• /status

**Voice Chat Controls**
• /join <chat_id>
• /leave <chat_id>
• /play (reply to audio)
• /silence
• /rush

**Recording**
• /record
• /stoprecord

**Sudo Management**
• /addsudo <user_id>
• /delsudo <user_id>

**Other**
• /help — Show this menu
"""
    await msg.reply(help_text)

# -------------------- BOT MAIN LOOP --------------------
async def main():
    await start_assistants()
    await bot.start()
    print("Bot started and ready.")
    await asyncio.get_event_loop().create_future()

if __name__ == "__main__":
    asyncio.run(main())