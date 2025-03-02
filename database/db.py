import os
import sqlite3
import discord
from pathlib import Path

# Ensure the data directory exists
data_dir = Path('./data')
data_dir.mkdir(exist_ok=True)

# Default settings
DEFAULT_EMBED_COLOR = discord.Color.blurple()  # Discord purple

class Database:
    def __init__(self, db_path='./data/guild_settings.db'):
        self.db_path = db_path
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize the database with required tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create settings table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            embed_color TEXT DEFAULT NULL
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_embed_color(self, guild_id):
        """Get the embed color for a guild, or return default if not set"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT embed_color FROM guild_settings WHERE guild_id = ?', 
            (guild_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            # Convert the stored hex color to discord.Color
            return discord.Color(int(result[0], 16))
        return DEFAULT_EMBED_COLOR
    
    def set_embed_color(self, guild_id, color_hex):
        """Set the embed color for a guild
        
        Args:
            guild_id: The Discord guild ID
            color_hex: Hex color string (e.g. "7289DA" for Discord Blurple)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate the hex color
            int(color_hex, 16)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'INSERT INTO guild_settings (guild_id, embed_color) VALUES (?, ?) '
                'ON CONFLICT(guild_id) DO UPDATE SET embed_color = ?',
                (guild_id, color_hex, color_hex)
            )
            
            conn.commit()
            conn.close()
            return True
        except ValueError:
            return False  # Invalid hex color