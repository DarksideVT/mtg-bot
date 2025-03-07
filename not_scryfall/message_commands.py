import re
import os
import discord
from .helpers import Helper
from discord.ui import Button, View
from scryfall.scryfall import ScryfallAPI


class MessagePaginationView(View):
    def __init__(self, helper, card, embed_type, guild_id=None, timeout=180):
        super().__init__(timeout=timeout)
        self.helper = helper
        self.card = card
        self.embed_type = embed_type
        self.guild_id = guild_id
        self.current_page = 0
        self.total_pages = None
        # Initialize buttons as disabled until setup is complete
        self.prev_page.disabled = True
        self.next_page.disabled = True

    async def setup(self):
        """Initialize the view with the first embed and page count"""
        embed, self.total_pages = await self.helper.create_paginated_embed(
            self.card, self.embed_type, 0, self.guild_id
        )
        self.prev_page.disabled = True
        self.next_page.disabled = self.total_pages <= 1
        return embed

    async def update_message(self, interaction: discord.Interaction):
        embed, self.total_pages = await self.helper.create_paginated_embed(
            self.card, self.embed_type, self.current_page, self.guild_id
        )
        self.prev_page.disabled = self.current_page <= 0
        self.next_page.disabled = self.current_page >= self.total_pages - 1
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def prev_page(self, button: Button, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_message(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_page(self, button: Button, interaction: discord.Interaction):
        if self.total_pages and self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self.update_message(interaction)


class MessageCommand:
    # Print if ALLOW_READ_MESSAGE is enabled when this module is imported
    if os.getenv("ALLOW_READ_MESSAGE", "true").lower() != "true":
        print("ALLOW_READ_MESSAGE!=true. Reading user messages DISABLED.")
    else:
        print("ALLOW_READ_MESSAGE=true. Reading user messages ENABLED.")

    def __init__(self, message: discord.Message, bot):
        self.message = message
        self.card_lookup = Helper(bot)
        self.guild_id = message.guild.id if message.guild else None

    async def image_lookup(self, card_name: str, set_code: str = None):
        embeds = await self.card_lookup.get_image_embed(card_name, set_code, self.guild_id)
        if not embeds:
            await self.message.reply("Could not fetch a card at the moment. Please try again later.")
            return
        for embed in embeds:
            await self.message.reply(embed=embed)

    async def price_lookup(self, card_name: str, set_code: str = None):
        embed = await self.card_lookup.get_price_embed(card_name, set_code, self.guild_id)
        if not embed:
            await self.message.reply("Could not fetch a card at the moment. Please try again later.")
            return
        await self.message.reply(embed=embed)

    async def rulings_lookup(self, card_name: str, set_code: str = None):
        card = await ScryfallAPI.get_rulings(card_name, set_code)
        if not card:
            await self.message.reply("Could not fetch a card at the moment. Please try again later.")
            return

        view = MessagePaginationView(self.card_lookup, card, "rulings", self.guild_id)
        embed = await view.setup()
        await self.message.reply(embed=embed, view=view if view.total_pages > 1 else None)

    async def legality_lookup(self, card_name: str, set_code: str = None):
        embed = await self.card_lookup.get_legality_embed(card_name, set_code, self.guild_id)
        if not embed:
            await self.message.reply("Could not fetch a card at the moment. Please try again later.")
            return
        await self.message.reply(embed=embed)

    async def default_lookup(self, card_name: str, set_code: str = None):
        embed = await self.card_lookup.get_card_embed(card_name, set_code, self.guild_id)
        if not embed:
            await self.message.reply("Could not fetch a card at the moment. Please try again later.")
            return
        await self.message.reply(embed=embed)

    async def sets_lookup(self, card_name: str, set_code: str = None):
        card = await ScryfallAPI.get_sets(card_name)
        if not card:
            await self.message.reply("Could not fetch sets at the moment. Please try again later.")
            return

        view = MessagePaginationView(self.card_lookup, card, "sets", self.guild_id)
        embed = await view.setup()
        await self.message.reply(embed=embed, view=view if view.total_pages > 1 else None)

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
        elif card_base.startswith("@"):
            await self.sets_lookup(card_base[1:], set_code)
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
