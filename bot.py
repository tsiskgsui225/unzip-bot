import asyncio

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from pyrogram import idle, Client
from Unzip.config import Config
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

app = Client(
    "unzip_bot",
    bot_token=Config.BOT_TOKEN,
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    plugins=dict(root="Unzip"),
    workers=50,
    sleep_threshold=10,
    max_concurrent_transmissions=50
)

async def main():
    await app.start()
    print("🎊 I AM ALIVE 🎊")
    await idle()
    await app.stop()

if __name__ == "__main__":
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
