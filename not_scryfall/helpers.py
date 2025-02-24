import re
import discord
from scryfall import scryfall


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

    def _create_embed(self, title, url, content=None, image_url=None):
        embed = discord.Embed(title=title, url=url, color=0x1F75FE)
        if content:
            embed.add_field(name="", value=content, inline=False)
        if image_url:
            embed.set_image(url=image_url)
        embed.set_footer(text="Data provided by Scryfall")
        return embed

    async def get_image_embed(self, card_name: str):
        card = scryfall.get_image(card_name)
        if not card:
            return None

        embeds = []
        embed = self._create_embed(card["name"], card["scryfall_uri"])
        if card["images"]:
            embed.set_image(url=card["images"][0])
            embeds.append(embed)

            if len(card["images"]) > 1:
                back_embed = self._create_embed(
                    f"{card['name']} (Back)",
                    card["scryfall_uri"],
                    image_url=card["images"][1]
                )
                embeds.append(back_embed)
        return embeds

    async def get_price_embed(self, card_name: str):
        card = scryfall.get_price(card_name)
        if not card:
            return None

        embed = self._create_embed(card["name"], card["scryfall_uri"])
        for edition in card["prices"]:
            embed.add_field(
                name=edition["set_name"],
                value=f'${edition["price"]}',
                inline=True
            )
        return embed

    async def get_rulings_embed(self, card_name: str):
        card = scryfall.get_rulings(card_name)
        if not card:
            return None

        embed = self._create_embed(
            f"Rulings for {card['name']}", card["scryfall_uri"])
        for ruling in card["rulings"][:8]:
            embed.add_field(name=ruling["date"],
                            value=ruling["text"], inline=False)

        if len(card["rulings"]) > 8:
            embed.add_field(
                name="Additional Rulings",
                value=f"[View {len(card['rulings']) - 8} more rulings on Scryfall]({card['scryfall_uri']})",
                inline=False
            )
        elif len(card["rulings"]) == 0:
            embed.add_field(
                name="No Rulings",
                value=f"No rulings available for {card['name']}",
                inline=False
            )
        return embed

    async def get_legality_embed(self, card_name: str):
        card = scryfall.get_legality(card_name)
        if not card:
            return None

        embed = self._create_embed(
            f"Legality for {card['name']}", card["scryfall_uri"])
        for legality in card["legalities"]:
            embed.add_field(name=legality["format"],
                            value=legality["status"], inline=True)
        return embed

    async def get_card_embed(self, card_name: str):
        card = scryfall.get_card(card_name)
        if not card:
            return None

        title = f'{card["name"]} {await self._format_mana_cost(card["mana_cost"])}'
        embed = self._create_embed(title, card["scryfall_uri"])
        embed.set_thumbnail(url=card["small_image"])
        embed.add_field(
            name=card["type_line"],
            value=await self._format_oracle_text(card['oracle_text']),
            inline=False
        )
        return embed
