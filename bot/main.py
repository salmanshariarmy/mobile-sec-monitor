#!/usr/bin/env python3
"""
Mobile Security Monitor — Discord Bot Entry Point
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands

from config import Config
from server.database import Database
from server.http_api import AlertAPI

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

class SecurityBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            activity=discord.Activity(type=discord.ActivityType.watching, name="for mobile threats 🛡️")
        )
        self.db = None
        self.http_api = None
        self.http_host = Config.HTTP_HOST
        self.http_port = Config.HTTP_PORT

    async def setup_hook(self):
        self.db = Database()
        logger.info(f"Database initialized at {self.db.db_path}")
        cog_dir = Path(__file__).parent / "cogs"
        for cog_file in cog_dir.glob("*.py"):
            if cog_file.name.startswith("_"):
                continue
            try:
                await self.load_extension(f"cogs.{cog_file.stem}")
                logger.info(f"Loaded cog: {cog_file.stem}")
            except Exception as e:
                logger.error(f"Failed to load {cog_file.stem}: {e}")
        self.http_api = AlertAPI(self, self.db)
        await self.http_api.start()
        await self.tree.sync()
        logger.info("Commands synced")

    async def on_ready(self):
        logger.info(f"✅ Bot online as {self.user} (ID: {self.user.id})")
        logger.info(f"🌐 HTTP API: {self.http_host}:{self.http_port}")
        logger.info(f"📊 Total guilds: {len(self.guilds)}")

async def main():
    try:
        Config.validate()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    bot = SecurityBot()
    async with bot:
        await bot.start(Config.BOT_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down.")
