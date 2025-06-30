import os
from pyrogram import Client, filters
from pytgcalls import PyTgCalls, idle
from pytgcalls.types.stream import AudioPiped
from youtubesearchpython import VideosSearch
from dotenv import load_dotenv
import yt_dlp

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_NAME = os.getenv("SESSION_NAME")

# Initialize clients
app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
pytgcalls = PyTgCalls(app)

# Audio queue for each chat
queues = {}

# Ensure downloads folder exists
os.makedirs("downloads", exist_ok=True)

# Function to download YouTube audio
def download_audio(url):
    ydl_opts = {
        'format': 'bestaudio',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# /play command
@app.on_message(filters.command("play") & (filters.group | filters.private))
async def play(_, message):
    chat_id = message.chat.id
    query = " ".join(message.command[1:])
    if not query:
        return await message.reply("❗Please enter a song name or YouTube link.")

    # Search YouTube
    results = VideosSearch(query, limit=1).result()["result"]
    if not results:
        return await message.reply("❌ No results found.")
    url = results[0]["link"]
    title = results[0]["title"]

    # Download audio
    try:
        file_path = download_audio(url)
    except Exception as e:
        return await message.reply(f"❌ Download error: {e}")

    # Play or queue
    if chat_id in queues and queues[chat_id]:
        queues[chat_id].append(file_path)
        await message.reply(f"🎶 Queued: **{title}**")
    else:
        queues[chat_id] = [file_path]
        try:
            await pytgcalls.join_group_call(
                chat_id,
                AudioPiped(file_path),
            )
            await message.reply(f"▶️ Now playing: **{title}**")
        except Exception as e:
            await message.reply(f"⚠️ Error joining voice chat: {e}")

# /skip command
@app.on_message(filters.command("skip") & filters.group)
async def skip(_, message):
    chat_id = message.chat.id
    if chat_id not in queues or not queues[chat_id]:
        return await message.reply("❗Nothing to skip.")

    # Remove current song
    queues[chat_id].pop(0)

    if queues[chat_id]:
        next_song = queues[chat_id][0]
        await pytgcalls.change_stream(
            chat_id,
            AudioPiped(next_song),
        )
        await message.reply("⏭ Skipped. Playing next song.")
    else:
        await pytgcalls.leave_group_call(chat_id)
        queues.pop(chat_id)
        await message.reply("🛑 Queue ended. Left voice chat.")

# /stop command
@app.on_message(filters.command("stop") & filters.group)
async def stop(_, message):
    chat_id = message.chat.id
    await pytgcalls.leave_group_call(chat_id)
    queues.pop(chat_id, None)
    await message.reply("🛑 Stopped and cleared the queue.")

# Start bot and voice client
async def main():
    await app.start()
    await pytgcalls.start()
    print("✅ Bot is up and running!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
