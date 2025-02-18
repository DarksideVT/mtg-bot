import os
from datetime import datetime

import discord
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Create the bot instance
bot = discord.Bot(intents=discord.Intents.default())

# Initialize the scheduler
scheduler = AsyncIOScheduler()


@bot.event
async def on_ready():
    print("Running")
    scheduler.start()

    # Read environment variables
    cron_schedule = os.getenv("CRON_SCHEDULE", "").strip()
    channel_id = os.getenv("CHANNEL_ID", "").strip()

    if cron_schedule and channel_id.isdigit():
        try:
            channel_id = int(channel_id)
            channel = bot.get_channel(channel_id)
            job = scheduler.add_job(
                send_scheduled_card,
                CronTrigger.from_crontab(cron_schedule),
                args=[channel_id],
            )
            next_run_time = job.next_run_time
            if next_run_time:
                time_until_next_run = next_run_time - datetime.now(next_run_time.tzinfo)
                formatted_time_until_next_run = str(time_until_next_run).split(".")[0]
                print(
                    f"Next scheduled card posting set to {next_run_time} in {formatted_time_until_next_run} hours.\nConfigured posting channel {channel.name} ({channel.id})."
                )
        except Exception as e:
            print(f"Error setting up scheduled job: {e}")


# Fetch a random MTG card from Scryfall
def get_random_card():
    url = "https://api.scryfall.com/cards/random"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        if "card_faces" in data:
            images = [
                face["image_uris"]["large"]
                for face in data["card_faces"]
                if "image_uris" in face
            ]
        else:
            images = [data["image_uris"]["large"]] if "image_uris" in data else []

        return {
            "name": data.get("name"),
            "images": images,  # Store all images
            "scryfall_uri": data.get("scryfall_uri"),
        }

    return None


# Slash command to fetch a random MTG card
@bot.slash_command(
    # This command can be used by guild members, but also by users anywhere if they install it
    integration_types={
        discord.IntegrationType.guild_install,
        discord.IntegrationType.user_install,
    },
    description="Fetch a random Magic: The Gathering card from Scryfall.",
    name="random-mtg-card",
)
async def random_card(ctx):
    card = get_random_card()
    if card:
        embed = discord.Embed(
            title=card["name"], url=card["scryfall_uri"], color=0x1F75FE
        )

        # Show first image
        if card["images"]:
            embed.set_image(url=card["images"][0])

            # If there are multiple faces, add a second image as a separate message
            if len(card["images"]) > 1:
                await ctx.respond(embed=embed)
                embed = discord.Embed(
                    title=f"{card['name']} (Back)",
                    url=card["scryfall_uri"],
                    color=0x1F75FE,
                )
                embed.set_image(url=card["images"][1])

        embed.set_footer(text="Data provided by Scryfall")
        await ctx.respond(embed=embed)
    else:
        await ctx.respond(
            "Could not fetch a card at the moment. Please try again later."
        )


# Function to send a scheduled random card
async def send_scheduled_card(channel_id):
    card = get_random_card()
    if not card:
        print("Failed to fetch a card.")
        return

    channel = bot.get_channel(channel_id)
    if not channel:
        print(f"Error: Could not find channel {channel_id}")
        return

    embed = discord.Embed(title=card["name"], url=card["scryfall_uri"], color=0x1F75FE)
    if card["image"]:
        embed.set_image(url=card["image"])
    embed.set_footer(text="Data provided by Scryfall")

    await channel.send(embed=embed)
    print(f"Sent scheduled card to channel {channel_id}")


# Run the bot
if __name__ == "__main__":
    bot_token = os.getenv("BOT_TOKEN", "").strip()

    if not bot_token:
        print("Error: BOT_TOKEN environment variable is empty or not set.")
        exit(1)

    bot.run(bot_token)
