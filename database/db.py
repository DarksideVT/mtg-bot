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
            embed_color TEXT DEFAULT NULL,
            random_card_schedule TEXT DEFAULT NULL,
            random_card_channel_id INTEGER DEFAULT NULL
        )
        ''')
        # Check and add columns if they don't exist
        cursor.execute("PRAGMA table_info(guild_settings)")
        columns = [info[1] for info in cursor.fetchall()]

        if 'random_card_schedule' not in columns:
            cursor.execute('''
            ALTER TABLE guild_settings
            ADD COLUMN random_card_schedule TEXT DEFAULT NULL
            ''')

        if 'random_card_channel_id' not in columns:
            cursor.execute('''
            ALTER TABLE guild_settings
            ADD COLUMN random_card_channel_id INTEGER DEFAULT NULL
            ''')

        if 'embed_color' not in columns:
            cursor.execute('''
            ALTER TABLE guild_settings
            ADD COLUMN embed_color TEXT DEFAULT NULL
            ''')
        
        conn.commit()
        conn.close()
    def get_guild_settings(self, guild_id):
        """Get the settings for a guild, or return None if not set"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT embed_color, random_card_schedule, random_card_channel_id '
            'FROM guild_settings WHERE guild_id = ?', 
            (guild_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'embed_color': discord.Color(int(result[0], 16)) if result[0] else DEFAULT_EMBED_COLOR,
                'random_card_schedule': result[1],
                'random_card_channel_id': result[2]
            }
        return None
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
    def get_random_card_schedule(self, guild_id):
        """Get the random card schedule for a guild, or return None if not set"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT random_card_schedule FROM guild_settings WHERE guild_id = ?', 
            (guild_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    def set_random_card_schedule(self, guild_id, schedule):
        """Set the random card schedule for a guild
        
        Args:
            guild_id: The Discord guild ID
            schedule: The schedule string
        
        Returns:
            bool: True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO guild_settings (guild_id, random_card_schedule) VALUES (?, ?) '
            'ON CONFLICT(guild_id) DO UPDATE SET random_card_schedule = ?',
            (guild_id, schedule, schedule)
        )
        
        conn.commit()
        conn.close()
        return True
    def get_random_card_channel_id(self, guild_id):
        """Get the random card channel ID for a guild, or return None if not set"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT random_card_channel_id FROM guild_settings WHERE guild_id = ?', 
            (guild_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    def set_random_card_channel_id(self, guild_id, channel_id):
        """Set the random card channel ID for a guild

        Args:
            guild_id: The Discord guild ID
            channel_id: The channel ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO guild_settings (guild_id, random_card_channel_id) VALUES (?, ?) '
            'ON CONFLICT(guild_id) DO UPDATE SET random_card_channel_id = ?',
            (guild_id, channel_id, channel_id)
        )
        
        conn.commit()
        conn.close()
        return True