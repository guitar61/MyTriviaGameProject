import os
import sys
import logging
from pathlib import Path

# Set the Django settings module FIRST
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TriviaBot.settings")

# Get the absolute path of the project directory
project_path = Path(__file__).resolve().parent.parent.parent
if project_path not in sys.path:
    sys.path.insert(0, str(project_path))

# Django setup
import django
django.setup()

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage  # Use MemoryStorage
from aiogram.utils import executor
from bot.telegram_bot.handlers import register_handlers  # Import AFTER initializing dp

# Configure logging
logging.basicConfig(level=logging.INFO)


# Bot Initialization
API_TOKEN = "7232722087:AAERMWSHCHFd3nYcIDL0479CVeLACNBHMHI"

bot = Bot(API_TOKEN)
storage = MemoryStorage()  # Replace RedisStorage2 with MemoryStorage
dp = Dispatcher(bot, storage=storage)

# Register all handlers
register_handlers(dp)

# Graceful startup/shutdown handling
async def on_startup(dp):
    logging.info("Bot is starting...")

async def on_shutdown(dp):
    await bot.close()
    await storage.close()
    logging.info("Bot is shutting down...")

if __name__ == "__main__":
    logging.info("Starting Trivia Bot...")
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown, skip_updates=True)
