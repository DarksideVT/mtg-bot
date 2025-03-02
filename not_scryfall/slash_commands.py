import os
import discord
from .helpers import Helper
from discord.ui import Button, View
from scryfall.scryfall import ScryfallAPI
from database.db import Database


class PaginationView(View):
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


class SlashCommand:
    def __init__(self, bot):
        self.bot: discord.AutoShardedBot = bot
        self.card_lookup = Helper(bot)
        self.db = Database()
        self.register_commands()

    def register_commands(self):
        self._register_random_command()
        self._register_card_command()
        self._register_image_command()
        self._register_price_command()
        self._register_rulings_command()
        self._register_legality_command()
        self._register_help_command()
        self._register_sets_command()
        self._register_settings_command()

    def _register_random_command(self):
        if os.getenv("ENABLE_RANDOM_COMMAND", "true").lower() != "true":
            print("ENABLE_RANDOM_COMMAND!=true. Random Card slash command DISABLED.")
            return
        print("ENABLE_RANDOM_COMMAND=true. Random Card slash command ENABLED.")

        @self.bot.command(
            description="Fetch a random Magic: The Gathering card from Scryfall.",
            name="random-card"
        )
        async def random_card(ctx):
            guild_id = ctx.guild.id if ctx.guild else None
            embeds = await self.card_lookup.get_image_embed("random", None, guild_id)
            if not embeds:
                await ctx.respond("Could not fetch a card at the moment. Please try again later.")
                return
            await ctx.respond(embed=embeds[0])
            if len(embeds) > 1:
                await ctx.respond(embed=embeds[1])

    def _register_card_command(self):
        if os.getenv("ENABLE_CARD_INFO_COMMAND", "true").lower() != "true":
            print("ENABLE_CARD_INFO_COMMAND!=true. Card Info slash command DISABLED.")
            return
        print("ENABLE_CARD_INFO_COMMAND=true. Card Info slash command ENABLED.")

        @self.bot.command(
            description="Fetch a specific Magic: The Gathering card from Scryfall.",
            name="card-info"
        )
        async def card(
            ctx,
            card_name: str = discord.Option(
                description="Name of the card", name="card-name"),
            set_code: str = discord.Option(
                description="Set code (optional)", name="set", required=False)
        ):
            guild_id = ctx.guild.id if ctx.guild else None
            embed = await self.card_lookup.get_card_embed(card_name, set_code, guild_id)
            if not embed:
                await ctx.respond("Could not fetch a card at the moment. Please try again later.")
                return
            await ctx.respond(embed=embed)

    def _register_image_command(self):
        if os.getenv("ENABLE_IMAGE_COMMAND", "true").lower() != "true":
            print("ENABLE_IMAGE_COMMAND!=true. Image slash command DISABLED.")
            return
        print("ENABLE_IMAGE_COMMAND=true. Image slash command ENABLED.")

        @self.bot.command(
            description="Fetch a specific Magic: The Gathering card's image from Scryfall.",
            name="image"
        )
        async def image(
            ctx,
            card_name: str = discord.Option(
                description="Name of the card", name="card-name"),
            set_code: str = discord.Option(
                description="Set code (optional)", name="set", required=False)
        ):
            guild_id = ctx.guild.id if ctx.guild else None
            embeds = await self.card_lookup.get_image_embed(card_name, set_code, guild_id)
            if not embeds:
                await ctx.respond("Could not fetch a card at the moment. Please try again later.")
                return
            await ctx.respond(embed=embeds[0])
            if len(embeds) > 1:
                await ctx.respond(embed=embeds[1])

    def _register_price_command(self):
        if os.getenv("ENABLE_PRICE_COMMAND", "true").lower() != "true":
            print("ENABLE_PRICE_COMMAND!=true. Price slash command DISABLED.")
            return
        print("ENABLE_PRICE_COMMAND=true. Price slash command ENABLED.")

        @self.bot.command(
            description="Fetch a specific Magic: The Gathering card's price from Scryfall.",
            name="price"
        )
        async def price(
            ctx,
            card_name: str = discord.Option(
                description="Name of the card", name="card-name"),
            set_code: str = discord.Option(
                description="Set code (optional)", name="set", required=False)
        ):
            guild_id = ctx.guild.id if ctx.guild else None
            card = await self.card_lookup.get_price_embed(card_name, set_code, guild_id)
            if not card:
                await ctx.respond("Could not fetch a card at the moment. Please try again later.")
                return
            await ctx.respond(embed=card)

    def _register_rulings_command(self):
        if os.getenv("ENABLE_RULINGS_COMMAND", "true").lower() != "true":
            print("ENABLE_RULINGS_COMMAND!=true. Rulings slash command DISABLED.")
            return
        print("ENABLE_RULINGS_COMMAND=true. Rulings slash command ENABLED.")

        @self.bot.command(
            description="Fetch a specific Magic: The Gathering card's rulings from Scryfall.",
            name="rulings"
        )
        async def rulings(ctx, card_name: str, set_code: str = None):
            guild_id = ctx.guild.id if ctx.guild else None
            card = await ScryfallAPI.get_rulings(card_name, set_code)
            if not card:
                await ctx.respond("Could not fetch a card at the moment. Please try again later.")
                return

            view = PaginationView(self.card_lookup, card, "rulings", guild_id)
            embed = await view.setup()
            await ctx.respond(embed=embed, view=view if view.total_pages > 1 else None)

    def _register_legality_command(self):
        if os.getenv("ENABLE_LEGALITY_COMMAND", "true").lower() != "true":
            print("ENABLE_LEGALITY_COMMAND!=true. Legality slash command DISABLED.")
            return
        print("ENABLE_LEGALITY_COMMAND=true. Legality slash command ENABLED.")

        @self.bot.command(
            description="Fetch a specific Magic: The Gathering card's legality from Scryfall.",
            name="legality"
        )
        async def legality(
            ctx,
            card_name: str = discord.Option(
                description="Name of the card", name="card-name"),
            set_code: str = discord.Option(
                description="Set code (optional)", name="set", required=False)
        ):
            guild_id = ctx.guild.id if ctx.guild else None
            card = await self.card_lookup.get_legality_embed(card_name, set_code, guild_id)
            if not card:
                await ctx.respond("Could not fetch a card at the moment. Please try again later.")
                return
            await ctx.respond(embed=card)

    def _register_sets_command(self):
        if os.getenv("ENABLE_SETS_COMMAND", "true").lower() != "true":
            print("ENABLE_SETS_COMMAND!=true. Sets slash command DISABLED.")
            return
        print("ENABLE_SETS_COMMAND=true. Sets slash command ENABLED.")

        @self.bot.command(
            description="Show all sets that contain a specific Magic: The Gathering card.",
            name="sets"
        )
        async def sets(ctx, card_name: str):
            guild_id = ctx.guild.id if ctx.guild else None
            card = await ScryfallAPI.get_sets(card_name)
            if not card:
                await ctx.respond("Could not fetch sets at the moment. Please try again later.")
                return

            view = PaginationView(self.card_lookup, card, "sets", guild_id)
            embed = await view.setup()
            await ctx.respond(embed=embed, view=view if view.total_pages > 1 else None)

    def _register_settings_command(self):
        @self.bot.command(
            description="Change or view bot settings for this server.",
            name="settings"
        )
        async def settings(
            ctx,
            action: str = discord.Option(
                description="Action to perform",
                choices=["view", "set"],
                required=True
            ),
            setting: str = discord.Option(
                description="Setting to change or view",
                choices=["embed-color"],
                required=False
            ),
            value: str = discord.Option(
                description="Value to set (use hex color code for embed colors, e.g. 7289DA)",
                required=False
            )
        ):
            # Check if in a guild context
            if not ctx.guild:
                await ctx.respond("Settings can only be changed in a server.", ephemeral=True)
                return
                
            guild_id = ctx.guild.id
            
            if action == "view":
                # View current settings
                embed = discord.Embed(
                    title=f"Settings for {ctx.guild.name}",
                    color=self.db.get_embed_color(guild_id)
                )
                
                # Get the current embed color
                current_color = self.db.get_embed_color(guild_id)
                hex_color = f"#{current_color.value:06X}"
                
                embed.add_field(
                    name="Embed Color",
                    value=f"Current color: {hex_color}",
                    inline=False
                )
                
                embed.set_footer(text="Use /settings set to change these settings")
                await ctx.respond(embed=embed)
                return
            
            elif action == "set":
                # Check for manage guild permissions
                if not ctx.author.guild_permissions.manage_guild:
                    await ctx.respond("You need the 'Manage Server' permission to change settings.", ephemeral=True)
                    return
                
                # Check if setting and value are provided
                if not setting:
                    await ctx.respond("Please specify a setting to change.", ephemeral=True)
                    return
                
                if not value:
                    await ctx.respond("Please specify a value for the setting.", ephemeral=True)
                    return
                
                if setting == "embed-color":
                    # Remove # prefix if present
                    if value.startswith("#"):
                        value = value[1:]
                    
                    # Validate hex color format
                    if not (len(value) == 6 and all(c in "0123456789ABCDEFabcdef" for c in value)):
                        await ctx.respond(
                            "Invalid color format. Please use a 6-digit hex color code (e.g., 7289DA for Discord Blurple).", 
                            ephemeral=True
                        )
                        return
                    
                    success = self.db.set_embed_color(guild_id, value)
                    if success:
                        # Create an embed with the new color to show as an example
                        new_color = discord.Color(int(value, 16))
                        embed = discord.Embed(
                            title="Embed Color Updated",
                            description=f"Embeds will now use this color: `#{value}`",
                            color=new_color
                        )
                        await ctx.respond(embed=embed)
                    else:
                        await ctx.respond("Failed to update embed color. Please try again.", ephemeral=True)
                else:
                    await ctx.respond(f"Unknown setting: {setting}", ephemeral=True)
            else:
                await ctx.respond(f"Unknown action: {action}", ephemeral=True)

    def _register_help_command(self):
        @self.bot.command(
            description="Display help for all available commands.",
            name="help"
        )
        async def help(ctx):
            guild_id = ctx.guild.id if ctx.guild else None
            embed = discord.Embed(
                title="Scryfall Bot Help",
                description=f"Here are the available commands for the {self.bot.user.display_name} bot.",
                color=self.db.get_embed_color(guild_id)
            )

            if os.getenv("ENABLE_RANDOM_COMMAND", "true").lower() == "true":
                embed.add_field(
                    name="/random-card",
                    value="Fetch a random Magic: The Gathering card from Scryfall.",
                    inline=False,
                )

            if os.getenv("ENABLE_CARD_INFO_COMMAND", "true").lower() == "true":
                embed.add_field(
                    name="/card-info [card-name]",
                    value="Fetch a specific Magic: The Gathering card from Scryfall.",
                    inline=False,
                )

            if os.getenv("ENABLE_IMAGE_COMMAND", "true").lower() == "true":
                embed.add_field(
                    name="/image [card-name]",
                    value="Fetch a specific Magic: The Gathering card's image from Scryfall.",
                    inline=False,
                )

            if os.getenv("ENABLE_PRICE_COMMAND", "true").lower() == "true":
                embed.add_field(
                    name="/price [card-name]",
                    value="Fetch a specific Magic: The Gathering card's price from Scryfall.",
                    inline=False,
                )

            if os.getenv("ENABLE_RULINGS_COMMAND", "true").lower() == "true":
                embed.add_field(
                    name="/rulings [card-name]",
                    value="Fetch a specific Magic: The Gathering card's rulings from Scryfall.",
                    inline=False,
                )

            if os.getenv("ENABLE_LEGALITY_COMMAND", "true").lower() == "true":
                embed.add_field(
                    name="/legality [card-name]",
                    value="Fetch a specific Magic: The Gathering card's legality from Scryfall.",
                    inline=False,
                )

            if os.getenv("ENABLE_SETS_COMMAND", "true").lower() == "true":
                embed.add_field(
                    name="/sets [card-name]",
                    value="Show all sets that contain a specific Magic: The Gathering card.",
                    inline=False,
                )
            
            # Always show settings command with updated description
            embed.add_field(
                name="/settings [action] [setting] [value]",
                value="View or change bot settings for this server.\n" +
                      "Examples:\n" +
                      "- `/settings view` - View all current settings\n" +
                      "- `/settings set embed-color 7289DA` - Change embed color (requires 'Manage Server' permission)",
                inline=False
            )

            await ctx.respond(embed=embed, ephemeral=True)
