import re
import aiohttp
import asyncio
import time
from typing import Optional


class ScryfallAPI:
    BASE_URL = "https://api.scryfall.com"
    _session = None
    _semaphore = asyncio.Semaphore(10)  # Max 10 concurrent requests
    _last_request_time = 0
    _min_delay = 0.1  # 100ms between requests (10 per second)

    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        """Get or create aiohttp ClientSession"""
        if cls._session is None:
            cls._session = aiohttp.ClientSession()
        return cls._session

    @classmethod
    async def close(cls):
        """Close the session"""
        if cls._session:
            await cls._session.close()
            cls._session = None

    @classmethod
    async def _rate_limited_request(cls, url: str) -> Optional[dict]:
        """Make a rate-limited request to Scryfall"""
        # Ensure minimum delay between requests
        current_time = time.time()
        time_since_last = current_time - cls._last_request_time
        if time_since_last < cls._min_delay:
            await asyncio.sleep(cls._min_delay - time_since_last)

        async with cls._semaphore:
            session = await cls.get_session()
            cls._last_request_time = time.time()
            async with session.get(url) as response:
                return await response.json() if response.status == 200 else None

    @classmethod
    async def _get_card_named(cls, card_name: str, set_code: str = None) -> Optional[dict]:
        """Base method to fetch a card by name"""
        if set_code:
            url = f"{cls.BASE_URL}/cards/named?fuzzy={card_name}&set={set_code}"
        else:
            url = f"{cls.BASE_URL}/cards/named?fuzzy={card_name}"
        return await cls._rate_limited_request(url)

    @classmethod
    async def _get_card_random(cls) -> Optional[dict]:
        """Base method to fetch a random card"""
        url = f"{cls.BASE_URL}/cards/random"
        return await cls._rate_limited_request(url)

    @staticmethod
    def _get_card_images(data: dict) -> list:
        """Helper method to extract card images"""
        if "card_faces" in data and "image_uris" in data["card_faces"][0]:
            image = data["card_faces"][0]["image_uris"]["large"]
        else:
            image = data["image_uris"]["large"] if "image_uris" in data else None
        return [image] if image else []

    @staticmethod
    def _get_mana_types(mana: str) -> list:
        """Helper method to parse mana symbols"""
        if not mana:
            return []
        reg = r"\{([^}]+)\}"
        mana_types = re.findall(reg, mana)
        return [f'mana{mana_type.lower()}' for mana_type in mana_types]
    
    @classmethod
    async def search_cards(cls, query: str, page: int = 1) -> Optional[dict]:
        """
        Search for cards using the Scryfall search API
        
        Args:
            query: The search query
            page: Page number (starts at 1)
        
        Returns:
            dict with search results or None if error
        """
        # Encode the query for URL
        encoded_query = query.replace(' ', '+')
        
        # Calculate pagination parameters (Scryfall uses 0-based page index)
        page_size = 10  # Number of results per page
        page_index = page - 1  # Convert to 0-based indexing
        
        url = f"{cls.BASE_URL}/cards/search?q={encoded_query}&page={page_index}&order=name"
        data = await cls._rate_limited_request(url)
        
        if not data:
            return None
            
        # Process and simplify the result data
        result = {
            "has_more": data.get("has_more", False),
            "total_cards": data.get("total_cards", 0),
            "next_page": page + 1 if data.get("has_more", False) else None,
            "current_page": page,
            "cards": []
        }
        
        for card in data.get("data", []):
            # Extract essential card information
            card_info = {
                "id": card.get("id"),
                "name": card.get("name"),
                "set_name": card.get("set_name"),
                "set": card.get("set"),
                "collector_number": card.get("collector_number"),
                "rarity": card.get("rarity"),
                "scryfall_uri": card.get("scryfall_uri")
            }
            
            # Get image if available
            if "image_uris" in card:
                card_info["thumbnail"] = card["image_uris"].get("small")
            elif "card_faces" in card and "image_uris" in card["card_faces"][0]:
                card_info["thumbnail"] = card["card_faces"][0]["image_uris"].get("small")
            else:
                card_info["thumbnail"] = None
                
            result["cards"].append(card_info)
            
        return result

    @classmethod
    async def get_random_card(cls):
        data = await cls._get_card_random()
        if not data:
            return None

        return {
            "name": data.get("name"),
            "images": cls._get_card_images(data),
            "scryfall_uri": data.get("scryfall_uri"),
        }

    @classmethod
    async def get_rulings(cls, card_name: str, set_code: str = None) -> Optional[dict]:
        data = await cls._get_card_named(card_name, set_code)
        if not data:
            return None

        rulings_uri = data.get("rulings_uri")
        if rulings_uri:
            rulings_data = await cls._rate_limited_request(rulings_uri)
            if rulings_data:
                return {
                    "name": data.get("name"),
                    "scryfall_uri": data.get("scryfall_uri"),
                    "rulings": [
                        {
                            "date": ruling["published_at"],
                            "text": ruling["comment"],
                        }
                        for ruling in rulings_data["data"]
                    ],
                }
        return None

    @classmethod
    async def get_legality(cls, card_name: str, set_code: str = None):
        data = await cls._get_card_named(card_name, set_code)
        if not data:
            return None

        legalities = data.get("legalities")
        if legalities:
            return {
                "name": data.get("name"),
                "scryfall_uri": data.get("scryfall_uri"),
                "legalities": [
                    {
                        "format": legality.replace("_", " ").title(),
                        "status": legalities[legality].replace("_", " ").title(),
                    }
                    for legality in legalities
                ],
            }
        return None

    @classmethod
    async def get_price(cls, card_name: str, set_code: str = None) -> Optional[dict]:
        data = await cls._get_card_named(card_name, set_code)
        if not data:
            return None

        print_search = data.get("prints_search_uri")
        if print_search:
            print_data = await cls._rate_limited_request(print_search)
            if print_data:
                return {
                    "name": data.get("name"),
                    "scryfall_uri": data.get("scryfall_uri"),
                    "prices": [
                        {
                            "set_name": print["set_name"],
                            "price": print["prices"]["usd"],
                        }
                        for print in print_data["data"]
                        if print["prices"]["usd"]
                    ],
                }
        return None

    @classmethod
    async def get_image(cls, card_name: str, set_code: str = None):
        if card_name == "random":
            data = await cls._get_card_random()
        else:
            data = await cls._get_card_named(card_name, set_code)

        if not data:
            return None

        return {
            "name": data.get("name"),
            "images": cls._get_card_images(data),
            "scryfall_uri": data.get("scryfall_uri"),
        }

    @classmethod
    async def get_card(cls, card_name: str, set_code: str = None):
        data = await cls._get_card_named(card_name, set_code)
        if not data:
            return None

        return {
            "name": data.get("name"),
            "scryfall_uri": data.get("scryfall_uri"),
            "oracle_text": data.get("oracle_text"),
            "mana_cost": cls._get_mana_types(data.get("mana_cost")),
            "small_image": data["image_uris"]["small"],
            "type_line": data.get("type_line"),
            "oracle_text": data.get("oracle_text")
        }

    @classmethod
    async def get_sets(cls, card_name: str) -> Optional[dict]:
        data = await cls._get_card_named(card_name)
        if not data:
            return None

        prints_search_uri = data.get("prints_search_uri")
        if prints_search_uri:
            prints_data = await cls._rate_limited_request(prints_search_uri)
            if prints_data:
                return {
                    "name": data.get("name"),
                    "scryfall_uri": data.get("scryfall_uri"),
                    "sets": [
                        {
                            "set_name": print["set_name"],
                            "set_code": print["set"],
                            "collector_number": print["collector_number"],
                            "released_at": print["released_at"]
                        }
                        for print in prints_data["data"]
                    ]
                }
        return None
