import os
import discord
from datetime import datetime
from .message_commands import MessageCommand
from .slash_commands import SlashCommand
from scryfall.scryfall import ScryfallAPI
from database.db import Database
from discord.ext import tasks
import croniter


class ScryfallBot:
    def __init__(self):
        # Setup bot configuration
        self.test_guild_id = os.getenv("TEST_GUILD_ID")
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        # Initialize bot
        if self.test_guild_id:
            print(f"Running in test mode with guild ID {self.test_guild_id}")
            self.bot = discord.AutoShardedBot(
                intents=intents, debug_guild=int(self.test_guild_id), )
        else:
            self.bot = discord.AutoShardedBot(intents=intents)
        self.bot.default_command_integration_types = {
            discord.IntegrationType.guild_install, discord.IntegrationType.user_install}

        # Setup event handlers
        self._setup_events()

        # Register commands - pass the ScryfallBot instance so slash commands can access it
        SlashCommand(self.bot, self)

        self.schedules = {}
        self.post_card_task.start()

    def _setup_events(self):
        @self.bot.event
        async def on_ready():
            self._load_schedules()
            print("Bot started.")

        @self.bot.event
        async def on_message(message: discord.Message):
            if message.author == self.bot.user:
                return
            if os.getenv("ALLOW_READ_MESSAGE", 'true').lower() == 'true':
                await MessageCommand.handle_message(message, self.bot)

        @self.bot.event
        async def on_close():
            await ScryfallAPI.close()

    def _load_schedules(self):
        db = Database()
        for guild in self.bot.guilds:
            guild_settings = db.get_guild_settings(guild.id)
            if guild_settings:
                cron_schedule = guild_settings['random_card_schedule']
                channel_id = guild_settings['random_card_channel_id']
                if cron_schedule and channel_id:
                    self.schedules[guild.id] = (cron_schedule, int(channel_id))

    def reload_guild_schedule(self, guild_id):
        """Reload the schedule for a specific guild from database"""
        db = Database()
        guild_settings = db.get_guild_settings(guild_id)
        # Remove existing schedule for this guild
        if guild_id in self.schedules:
            del self.schedules[guild_id]

        # Add updated schedule if both settings are present
        if guild_settings:
            cron_schedule = guild_settings['random_card_schedule']
            channel_id = guild_settings['random_card_channel_id']
            if cron_schedule and channel_id:
                self.schedules[guild_id] = (cron_schedule, int(channel_id))
            else:
                self.schedules.pop(guild_id, None)
        return True

    @tasks.loop(seconds=60)
    async def post_card_task(self):
        now = datetime.now()
        for guild_id, (cron_schedule, channel_id) in self.schedules.items():
            if self._is_time_to_post(cron_schedule, now):
                await self._send_scheduled_card(channel_id)

    def _is_time_to_post(self, cron_schedule, now):
        # Get the previous scheduled run time
        cron = croniter.croniter(cron_schedule, now)
        prev_run = cron.get_prev(datetime)
        next_run = cron.get_next(datetime)
        # If the difference between now and the previous run is less than 1 minute,
        # it means we're in the same minute when a post should occur
        time_since_prev = now - prev_run
        seconds_since_prev = time_since_prev.total_seconds()
        print(f"Seconds since previous run: {seconds_since_prev}")
        print(f"Next run: {next_run}")
        print(f"Now: {now}")
        # With a 60-second check interval, use the same window for posting
        return seconds_since_prev < 60

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

    async def close(self):
        """Cleanup and shutdown"""
        print("Shutting down...")
        # Removed scheduler shutdown
        await ScryfallAPI.close()
        await self.bot.close()
        self.post_card_task.cancel()

    def run(self):
        """Start the bot"""
        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if not bot_token:
            print("Error: BOT_TOKEN environment variable is empty or not set.")
            exit(1)
        self.bot.run(bot_token)
