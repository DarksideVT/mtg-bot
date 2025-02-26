import re
import discord
from .helpers import Helper


class MessageCommand:
    def __init__(self, message: discord.Message, bot):
        self.message = message
        self.card_lookup = Helper(bot)

    async def image_lookup(self, card_name: str, set_code: str = None):
        embeds = await self.card_lookup.get_image_embed(card_name, set_code)
        if not embeds:
            await self.message.reply("Could not fetch a card at the moment. Please try again later.")
            return
        for embed in embeds:
            await self.message.reply(embed=embed)

    async def price_lookup(self, card_name: str, set_code: str = None):
        embed = await self.card_lookup.get_price_embed(card_name, set_code)
        if not embed:
            await self.message.reply("Could not fetch a card at the moment. Please try again later.")
            return
        await self.message.reply(embed=embed)

    async def rulings_lookup(self, card_name: str, set_code: str = None):
        embed = await self.card_lookup.get_rulings_embed(card_name, set_code)
        if not embed:
            await self.message.reply("Could not fetch a card at the moment. Please try again later.")
            return
        await self.message.reply(embed=embed)

    async def legality_lookup(self, card_name: str, set_code: str = None):
        embed = await self.card_lookup.get_legality_embed(card_name, set_code)
        if not embed:
            await self.message.reply("Could not fetch a card at the moment. Please try again later.")
            return
        await self.message.reply(embed=embed)

    async def default_lookup(self, card_name: str, set_code: str = None):
        embed = await self.card_lookup.get_card_embed(card_name, set_code)
        if not embed:
            await self.message.reply("Could not fetch a card at the moment. Please try again later.")
            return
        await self.message.reply(embed=embed)

    async def process_card_name(self, card_name: str):
        # Split card name and set code if present
        card_parts = card_name.split('|')
        card_base = card_parts[0].strip()
        set_code = card_parts[1].strip() if len(card_parts) > 1 else None

        if card_base.startswith("!"):
            await self.image_lookup(card_base[1:], set_code)
        elif card_base.startswith("$"):
            await self.price_lookup(card_base[1:], set_code)
        elif card_base.startswith("?"):
            await self.rulings_lookup(card_base[1:], set_code)
        elif card_base.startswith("#"):
            await self.legality_lookup(card_base[1:], set_code)
        else:
            await self.default_lookup(card_base, set_code)

    @classmethod
    async def handle_message(cls, message: discord.Message, bot):
        if message.author == bot.user:
            return

        content = message.content
        card_lookup_regex = r"\[\[(.*?)\]\]"
        card_names = re.findall(card_lookup_regex, content)

        if not card_names:
            return

        command = cls(message, bot)
        for card_name in card_names:
            await command.process_card_name(card_name)
