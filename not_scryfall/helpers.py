import re
import discord
from scryfall.scryfall import ScryfallAPI
from typing import Optional
import math


class Helper:
    def __init__(self, bot):
        self.bot = bot

    async def _get_emoji_id(self, emoji_name: str):
        emojis = await self.bot.fetch_emojis()
        for emoji in emojis:
            if emoji.name == emoji_name.lower():
                return emoji.id
        return None

    async def _format_mana_cost(self, mana_cost: str):
        mana_string = ""
        for emoji in mana_cost:
            emoji_id = await self._get_emoji_id(emoji)
            if emoji_id:
                mana_string += f"<:{emoji}:{emoji_id}>"
            else:
                mana_string += f"{{{emoji}}}"
        return mana_string

    async def _format_oracle_text(self, oracle_text: str):
        mana_symbols = re.findall(r'\{.*?\}', oracle_text)
        for mana_symbol in mana_symbols:
            symbol = mana_symbol[1:-1]
            emoji_id = await self._get_emoji_id(f"mana{symbol}")
            if emoji_id:
                oracle_text = oracle_text.replace(
                    mana_symbol, f"<:mana{symbol}:{emoji_id}>")
        return oracle_text

    async def create_paginated_embed(self, card, embed_type="card", page=0):
        if not card:
            return None, None

        embed = discord.Embed(url=card["scryfall_uri"])
        embed.set_footer(text="Data provided by Scryfall")
        total_pages = 1

        if embed_type == "sets":
            sets_per_page = 24  # Leave room for page indicator field
            total_sets = len(card["sets"])
            total_pages = math.ceil(total_sets / sets_per_page)
            start_idx = page * sets_per_page
            end_idx = start_idx + sets_per_page

            embed.title = f"Sets for {card['name']} (Page {page + 1}/{total_pages})"
            for set_info in card["sets"][start_idx:end_idx]:
                embed.add_field(
                    name=set_info["set_name"],
                    value=f"Set Code: {set_info['set_code'].upper()}\n"
                    f"Collector Number: {set_info['collector_number']}\n"
                    f"Released: {set_info['released_at']}",
                    inline=True
                )

        elif embed_type == "rulings":
            rulings = card["rulings"]
            pages = []
            current_page = []
            current_chars = 0

            # First, group rulings into pages based on character count
            for ruling in rulings:
                # Truncate ruling text if it exceeds Discord's field value limit
                ruling_text = ruling["text"]
                if len(ruling_text) > 1024:
                    ruling_text = ruling_text[:1021] + "..."

                ruling_chars = len(ruling["date"]) + len(ruling_text)

                # If adding this ruling would exceed embed limit or max fields, start new page
                if current_chars + ruling_chars > 5500 or len(current_page) >= 24:
                    if current_page:
                        pages.append(current_page)
                    current_page = []
                    current_chars = 0

                current_page.append({
                    "date": ruling["date"],
                    "text": ruling_text
                })
                current_chars += ruling_chars

            # Add the last page if it has content
            if current_page:
                pages.append(current_page)

            if not pages:
                embed.title = f"Rulings for {card['name']}"
                embed.description = "No rulings found."
                return embed, 1

            total_pages = len(pages)
            page = min(page, total_pages - 1)  # Ensure page is in valid range

            embed.title = f"Rulings for {card['name']} (Page {page + 1}/{total_pages})"

            # Add rulings from the current page
            for ruling in pages[page]:
                embed.add_field(name=ruling["date"],
                                value=ruling["text"],
                                inline=False)

        else:
            # For other embed types, use the existing create_card_embed method
            embed = await self.create_card_embed(card, embed_type)
            return embed, total_pages

        return embed, total_pages

    async def create_card_embed(self, card, embed_type="card"):
        embed, _ = await self.create_paginated_embed(card, embed_type, 0)
        return embed

    async def get_image_embed(self, card_name: str, set_code: str = None):
        card = await ScryfallAPI.get_image(card_name, set_code)
        if not card:
            return None

        embeds = []
        embed = await self.create_card_embed(card, "image")
        if embed:
            embeds.append(embed)

            if len(card["images"]) > 1:
                card_back = dict(card)
                card_back["name"] = f"{card['name']} (Back)"
                card_back["images"] = [card["images"][1]]
                back_embed = await self.create_card_embed(card_back, "image")
                embeds.append(back_embed)
        return embeds

    async def get_price_embed(self, card_name: str, set_code: str = None):
        card = await ScryfallAPI.get_price(card_name, set_code)
        return await self.create_card_embed(card, "price")

    async def get_rulings_embed(self, card_name: str, set_code: str = None):
        card = await ScryfallAPI.get_rulings(card_name, set_code)
        return await self.create_card_embed(card, "rulings")

    async def get_legality_embed(self, card_name: str, set_code: str = None):
        card = await ScryfallAPI.get_legality(card_name, set_code)
        return await self.create_card_embed(card, "legality")

    async def get_card_embed(self, card_name: str, set_code: str = None):
        card = await ScryfallAPI.get_card(card_name, set_code)
        return await self.create_card_embed(card, "card")

    async def get_sets_embed(self, card_name: str) -> Optional[discord.Embed]:
        card_data = await ScryfallAPI.get_sets(card_name)
        return await self.create_card_embed(card_data, "sets")
