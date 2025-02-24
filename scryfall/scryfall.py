import re
import aiohttp


class ScryfallAPI:
    BASE_URL = "https://api.scryfall.com"
    _session = None

    @classmethod
    async def get_session(cls):
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
    async def _get_card_named(cls, card_name: str) -> dict:
        """Base method to fetch a card by name"""
        session = await cls.get_session()
        url = f"{cls.BASE_URL}/cards/named?fuzzy={card_name}"
        async with session.get(url) as response:
            return await response.json() if response.status == 200 else None

    @classmethod
    async def _get_card_random(cls) -> dict:
        """Base method to fetch a random card"""
        session = await cls.get_session()
        url = f"{cls.BASE_URL}/cards/random"
        async with session.get(url) as response:
            return await response.json() if response.status == 200 else None

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
    async def get_rulings(cls, card_name: str):
        data = await cls._get_card_named(card_name)
        if not data:
            return None

        rulings_uri = data.get("rulings_uri")
        if rulings_uri:
            session = await cls.get_session()
            async with session.get(rulings_uri) as response:
                if response.status == 200:
                    rulings_data = await response.json()
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
    async def get_legality(cls, card_name: str):
        data = await cls._get_card_named(card_name)
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
    async def get_price(cls, card_name: str):
        data = await cls._get_card_named(card_name)
        if not data:
            return None

        print_search = data.get("prints_search_uri")
        if print_search:
            session = await cls.get_session()
            async with session.get(print_search) as response:
                if response.status == 200:
                    print_data = await response.json()
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
    async def get_image(cls, card_name: str):
        if card_name == "random":
            data = await cls._get_card_random()
        else:
            data = await cls._get_card_named(card_name)

        if not data:
            return None

        return {
            "name": data.get("name"),
            "images": cls._get_card_images(data),
            "scryfall_uri": data.get("scryfall_uri"),
        }

    @classmethod
    async def get_card(cls, card_name: str):
        data = await cls._get_card_named(card_name)
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
