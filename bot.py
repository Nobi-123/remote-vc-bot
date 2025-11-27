import os
import json
import asyncio
from pyrogram import Client, filters
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped
from pydub import AudioSegment
from config import *

# -------------------- CONFIGURATION --------------------
# TEMP_DIR, SESSIONS_DIR, API_ID, API_HASH, BOT_TOKEN, OWNER_ID, PREFIX, sudo_users
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(SESSIONS_DIR, exist_ok=True)

silence_file = os.path.join(TEMP_DIR, "silence.mp3")
if not os.path.exists(silence_file):
    print("Creating silence.mp3...")
    AudioSegment.silent(duration=3000).export(silence_file, format="mp3")

state_file = "sessions.json"
session_files = []

if os.path.exists(state_file):
    with open(state_file, "r") as f:
        session_files = json.load(f)

# -------------------- GLOBAL STATE --------------------
bot = Client("vc-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
assistants = []
calls = {}
recording = False
silenced = False
paused_streams = {}

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

async def auto_reconnect(cli, chat_id, audio_file):
    while True:
        try:
            await calls[cli].join_group_call(chat_id, AudioPiped(audio_file))
            break
        except Exception:
            await asyncio.sleep(5)  # retry every 5 seconds

# -------------------- COMMANDS --------------------
@bot.on_message(filters.command("connect", PREFIX) & filters.user(sudo_users))
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

    await msg.reply(f"Session added: {sess_path}")

@bot.on_message(filters.command("disconnect", PREFIX) & filters.user(sudo_users))
async def disconnect(_, msg):
    if len(msg.command) < 2:
        return await msg.reply("Usage: /disconnect <session_number>")
    try:
        idx = int(msg.command[1]) - 1
        cli = assistants.pop(idx)
        await calls[cli].stop()
        await cli.stop()

        os.remove(session_files.pop(idx))
        save_sessions()
        await msg.reply("Session removed successfully")
    except Exception as e:
        await msg.reply(f"Error: {e}")

@bot.on_message(filters.command("join", PREFIX) & filters.user(sudo_users))
async def join(_, msg):
    if len(msg.command) < 2:
        return await msg.reply("Usage: /join <chat_id>")
    chat = int(msg.command[1])

    for cli in assistants:
        try:
            await cli.join_chat(chat)
            await calls[cli].join_group_call(chat, AudioPiped(silence_file))
        except Exception as e:
            print(f"Failed to join VC for {cli}: {e}")

    await msg.reply("Assistants tried joining VC")

@bot.on_message(filters.command("leave", PREFIX) & filters.user(sudo_users))
async def leave(_, msg):
    chat = int(msg.command[1]) if len(msg.command) > 1 else None
    for cli in assistants:
        try:
            await calls[cli].leave_group_call(chat)
        except Exception as e:
            print(f"Failed to leave VC for {cli}: {e}")
    await msg.reply("Assistants left VC")

@bot.on_message(filters.command("play", PREFIX) & filters.user(sudo_users))
async def play(_, msg):
    if not msg.reply_to_message:
        return await msg.reply("Reply to audio with /play")

    file_path = await msg.reply_to_message.download(os.path.join(TEMP_DIR, "play.mp3"))
    for cli in assistants:
        try:
            await calls[cli].change_stream(0, AudioPiped(file_path))
        except Exception as e:
            print(f"Failed to play audio for {cli}: {e}")
    await msg.reply("Playing audio")

@bot.on_message(filters.command("silence", PREFIX) & filters.user(sudo_users))
async def silence(_, msg):
    global silenced, paused_streams
    silenced = True
    paused_streams = {}
    for cli in assistants:
        try:
            paused_streams[cli] = calls[cli].get_active_call()
            await calls[cli].change_stream(0, AudioPiped(silence_file))
        except Exception as e:
            print(f"Failed to silence {cli}: {e}")
    await msg.reply("Audio muted (silence mode)")

@bot.on_message(filters.command("rush", PREFIX) & filters.user(sudo_users))
async def rush(_, msg):
    global silenced, paused_streams
    if not silenced:
        return await msg.reply("Bot is not silenced")
    silenced = False
    for cli, old_stream in paused_streams.items():
        try:
            if old_stream:
                await calls[cli].change_stream(0, old_stream)
        except Exception as e:
            print(f"Failed to resume {cli}: {e}")
    paused_streams = {}
    await msg.reply("Audio resumed")

@bot.on_message(filters.command("record", PREFIX) & filters.user(sudo_users))
async def start_record(_, msg):
    global recording
    recording = True
    await msg.reply("Recording started")

@bot.on_message(filters.command("stoprecord", PREFIX) & filters.user(sudo_users))
async def stop_record(_, msg):
    global recording
    recording = False
    await msg.reply("Recording stopped")

@bot.on_message(filters.command("status", PREFIX) & filters.user(sudo_users))
async def status(_, msg):
    text = f"""
📊 **Bot Status**
Assistants: {len(assistants)}
Sudo Users: {sudo_users}
Recording: {recording}
Silenced: {silenced}
"""
    await msg.reply(text)

@bot.on_message(filters.command("addsudo", PREFIX) & filters.user({OWNER_ID}))
async def addsudo(_, msg):
    if len(msg.command) < 2:
        return await msg.reply("Usage: /addsudo <user_id>")
    uid = int(msg.command[1])
    sudo_users.add(uid)
    await msg.reply(f"Added {uid} as sudo")

@bot.on_message(filters.command("delsudo", PREFIX) & filters.user({OWNER_ID}))
async def delsudo(_, msg):
    if len(msg.command) < 2:
        return await msg.reply("Usage: /delsudo <user_id>")
    uid = int(msg.command[1])
    sudo_users.discard(uid)
    await msg.reply(f"Removed {uid} from sudo")

@bot.on_message(filters.command("help", PREFIX) & filters.user(sudo_users | {OWNER_ID}))
async def help_cmd(_, msg):
    help_text = """
🔰 **VC Multi-Assistant Bot — Help Menu**

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

# -------------------- MAIN LOOP --------------------
async def main():
    await start_assistants()
    await bot.start()
    print("Bot started and ready")
    await asyncio.get_event_loop().create_future()

if __name__ == "__main__":
    asyncio.run(main())