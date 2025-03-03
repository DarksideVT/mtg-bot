import re
import discord
from scryfall.scryfall import ScryfallAPI
from typing import Optional
import math
from database.db import Database
import dateparser


class Helper:
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

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

    def _get_guild_embed_color(self, guild_id=None):
        """Get the appropriate embed color for a guild"""
        if guild_id:
            return self.db.get_embed_color(guild_id)
        return discord.Color.blurple()

    @staticmethod
    def parse_schedule(schedule_text):
        """
        Parse natural language schedule into cron expression
        
        Args:
            schedule_text: Natural language schedule (e.g., "Every day at 5PM")
        
        Returns:
            str: Cron expression or original text if can't be parsed
        """
        schedule_text = schedule_text.strip()
        
        # Try to identify recurring schedule patterns
        daily_pattern = re.search(r'(?:every|each)\s+day|daily', schedule_text, re.IGNORECASE)
        weekly_pattern = re.search(r'(?:every|each)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|mon|tue|wed|thu|fri|sat|sun)', schedule_text, re.IGNORECASE)
        
        # Try to parse time using dateparser
        # Create a reference time string
        time_ref = "at " + schedule_text.split("at ")[-1] if "at " in schedule_text else schedule_text
        parsed_time = dateparser.parse(time_ref)
        
        if not parsed_time:
            return schedule_text  # Return original if we can't parse the time
        
        # Extract hour and minute
        hour = parsed_time.hour
        minute = parsed_time.minute
        
        # Determine the schedule type and create appropriate cron expression
        if daily_pattern:
            return f"{minute} {hour} * * *"  # Every day at the specified time
        elif weekly_pattern:
            # Map weekday names to cron day numbers (0-6, where 0 is Sunday)
            days_mapping = {
                'monday': 1, 'mon': 1,
                'tuesday': 2, 'tue': 2,
                'wednesday': 3, 'wed': 3,
                'thursday': 4, 'thu': 4, 
                'friday': 5, 'fri': 5,
                'saturday': 6, 'sat': 6,
                'sunday': 0, 'sun': 0
            }
            
            day_of_week = None
            for day_name, day_num in days_mapping.items():
                if re.search(r'\b' + day_name + r'\b', schedule_text, re.IGNORECASE):
                    day_of_week = day_num
                    break
            
            if day_of_week is not None:
                return f"{minute} {hour} * * {day_of_week}"  # Every specified weekday at the specified time
            else:
                # If no specific day mentioned but "weekly", default to Monday
                return f"{minute} {hour} * * 1"
        
        # Default: if we can parse the time but not the recurrence pattern, assume daily
        return f"{minute} {hour} * * *"


    async def create_paginated_embed(self, card, embed_type="card", page=0, guild_id=None):
        if not card:
            return None, None

        # Create embed with guild-specific color
        embed = discord.Embed(
            url=card["scryfall_uri"],
            color=self._get_guild_embed_color(guild_id)
        )
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

        elif embed_type == "image":
            embed.title = card["name"]
            if "images" in card and card["images"]:
                embed.set_image(url=card["images"][0])
            
        elif embed_type == "price":
            if "prices" in card and card["prices"]:
                embed.title = f"Prices for {card['name']}"
                for price_data in card["prices"]:
                    embed.add_field(
                        name=price_data["set_name"],
                        value=f"${price_data['price']}",
                        inline=True
                    )
            else:
                embed.title = f"No price data for {card['name']}"
                embed.description = "This card may not be available for purchase or price data is unavailable."
                
        elif embed_type == "legality":
            if "legalities" in card and card["legalities"]:
                embed.title = f"Format Legality for {card['name']}"
                for legality in card["legalities"]:
                    embed.add_field(
                        name=legality["format"],
                        value=legality["status"],
                        inline=True
                    )
            else:
                embed.title = f"No legality data for {card['name']}"
                
        else:  # Default "card" embed type
            embed.title = card["name"]
            if "small_image" in card:
                embed.set_thumbnail(url=card["small_image"])
            if "type_line" in card:
                embed.add_field(name="Type", value=card["type_line"], inline=True)
            if "mana_cost" in card and card["mana_cost"]:
                mana_cost_formatted = await self._format_mana_cost(card["mana_cost"])
                embed.add_field(name="Mana Cost", value=mana_cost_formatted, inline=True)
            if "oracle_text" in card and card["oracle_text"]:
                oracle_text_formatted = await self._format_oracle_text(card["oracle_text"])
                embed.add_field(name="Oracle Text", value=oracle_text_formatted, inline=False)

        return embed, total_pages

    async def create_card_embed(self, card, embed_type="card", guild_id=None):
        if not card:
            return None
        embed, _ = await self.create_paginated_embed(card, embed_type, 0, guild_id)
        return embed

    async def get_image_embed(self, card_name: str, set_code: str = None, guild_id=None):
        card = await ScryfallAPI.get_image(card_name, set_code)
        if not card:
            return None

        embeds = []
        embed = await self.create_card_embed(card, "image", guild_id)
        if embed:
            embeds.append(embed)

            if len(card["images"]) > 1:
                card_back = dict(card)
                card_back["name"] = f"{card['name']} (Back)"
                card_back["images"] = [card["images"][1]]
                back_embed = await self.create_card_embed(card_back, "image", guild_id)
                embeds.append(back_embed)
        return embeds

    async def get_price_embed(self, card_name: str, set_code: str = None, guild_id=None):
        card = await ScryfallAPI.get_price(card_name, set_code)
        return await self.create_card_embed(card, "price", guild_id)

    async def get_rulings_embed(self, card_name: str, set_code: str = None, guild_id=None):
        card = await ScryfallAPI.get_rulings(card_name, set_code)
        return await self.create_card_embed(card, "rulings", guild_id)

    async def get_legality_embed(self, card_name: str, set_code: str = None, guild_id=None):
        card = await ScryfallAPI.get_legality(card_name, set_code)
        return await self.create_card_embed(card, "legality", guild_id)

    async def get_card_embed(self, card_name: str, set_code: str = None, guild_id=None):
        card = await ScryfallAPI.get_card(card_name, set_code)
        return await self.create_card_embed(card, "card", guild_id)

    async def get_sets_embed(self, card_name: str, guild_id=None) -> Optional[discord.Embed]:
        card_data = await ScryfallAPI.get_sets(card_name)
        return await self.create_card_embed(card_data, "sets", guild_id)
