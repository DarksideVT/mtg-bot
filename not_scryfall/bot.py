import os
import discord
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from .message_commands import MessageCommand
from .slash_commands import SlashCommand
from scryfall.scryfall import ScryfallAPI
import signal
import asyncio


class ScryfallBot:
    def __init__(self):
        # Setup bot configuration
        self.test_guild_id = os.getenv("TEST_GUILD_ID")
        intents = discord.Intents.default()
        intents.message_content = True

        # Initialize bot
        if self.test_guild_id:
            print(f"Running in test mode with guild ID {self.test_guild_id}")
            self.bot = discord.AutoShardedBot(
                intents=intents, debug_guild=int(self.test_guild_id), )
        else:
            self.bot = discord.AutoShardedBot(intents=intents)
        self.bot.default_command_integration_types = {
            discord.IntegrationType.guild_install, discord.IntegrationType.user_install}

        # Initialize scheduler
        self.scheduler = AsyncIOScheduler()

        # Setup event handlers
        self._setup_events()

        # Register commands
        SlashCommand(self.bot)

    def _setup_events(self):
        @self.bot.event
        async def on_ready():
            print("Bot started.")
            self.scheduler.start()
            await self._setup_scheduled_posts()

        @self.bot.event
        async def on_message(message: discord.Message):
            if message.author == self.bot.user:
                return
            if os.getenv("SCRYFALL_LOOKUP", 'true').lower() == 'true':
                await MessageCommand.handle_message(message, self.bot)

        @self.bot.event
        async def on_close():
            await ScryfallAPI.close()

    async def _setup_scheduled_posts(self):
        """Setup scheduled card posting if configured"""
        cron_schedule = os.getenv("CRON_SCHEDULE", "").strip()
        channel_id = os.getenv("CHANNEL_ID", "").strip()

        if cron_schedule and channel_id.isdigit():
            try:
                channel_id = int(channel_id)
                channel = self.bot.get_channel(channel_id)
                job = self.scheduler.add_job(
                    self._send_scheduled_card,
                    CronTrigger.from_crontab(cron_schedule),
                    args=[channel_id],
                )
                next_run_time = job.next_run_time
                if next_run_time:
                    time_until_next_run = next_run_time - \
                        datetime.now(next_run_time.tzinfo)
                    formatted_time = str(time_until_next_run).split(".")[0]
                    print(
                        f"Next scheduled card posting set to {next_run_time} "
                        f"in {formatted_time} hours.\n"
                        f"Configured posting channel {channel.name} ({channel.id})."
                    )
            except Exception as e:
                print(f"Error setting up scheduled job: {e}")

    async def _send_scheduled_card(self, channel_id: int):
        """Send a random card to the specified channel"""
        card = await ScryfallAPI.get_random_card()
        if not card:
            print("Failed to fetch a card.")
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            print(f"Error: Could not find channel {channel_id}")
            return

        embed = discord.Embed(
            title=card["name"],
            url=card["scryfall_uri"]
        )
        if card["images"]:
            embed.set_image(url=card["images"][0])
        embed.set_footer(text="Data provided by Scryfall")

        await channel.send(embed=embed)
        print(f"Sent scheduled card to channel {channel_id}")

    async def close(self):
        """Cleanup and shutdown"""
        print("Shutting down...")
        self.scheduler.shutdown()
        await ScryfallAPI.close()
        await self.bot.close()

    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        def signal_handler(sig, frame):
            print("Received shutdown signal...")
            asyncio.get_event_loop().run_until_complete(self.close())
            exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def run(self):
        """Start the bot"""
        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if not bot_token:
            print("Error: BOT_TOKEN environment variable is empty or not set.")
            exit(1)

        self._setup_signal_handlers()
        self.bot.run(bot_token)


def run_bot():
    """Entry point to start the bot"""
    bot = ScryfallBot()
    bot.run()


if __name__ == "__main__":
    run_bot()
