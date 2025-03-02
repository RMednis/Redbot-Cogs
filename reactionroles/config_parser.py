from datetime import datetime

import discord


class ConfigError(Exception):
    pass
async def find_embed(configs: list, name: str) -> dict:
    for config in configs:
        if config["name"] == name:
            return config

    raise ConfigError(f"Embed '{name}' not found")

async def find_embed_by_id(configs: list, message_id: int) -> dict|None:
    for config in configs:
        if config["message"] == message_id:
            return config

    return None

async def embed_exists(configs: list, name: str) -> bool:
    for config in configs:
        if config["name"] == name:
            return True

    return False

async def has_fields(config: dict) -> bool:
    if "fields" in config:
        if isinstance(config["fields"], list):
            if len(config["fields"]) > 0:
                return True
    return False

async def has_reaction_roles(config: dict) -> bool:
    if "reaction_roles" in config:
        if config["reaction_roles"] is not None:
            return True

async def get_reaction_roles(config: dict, emoji: str) -> list:
    roles = []
    for role in config["reaction_roles"]:
        if role["emoji"] == emoji:
            roles.append(role)

    return roles

async def get_color(color: str) -> int:
    if color.startswith("#"):
        color = color[1:]

    return int(color, 16)

async def check_keys(config: dict, keys: list) -> bool:
    # Check if the config contains the required keys
    for key in keys:
        if key not in config:
            raise ConfigError(f"Missing key: {key}")

    return True

async def parse_config(config: dict) -> bool:
    # Check if the config contains the required keys
    required_keys = ["name", "channel","message", "color"]
    await check_keys(config, required_keys)

    # Check if the keys are of the correct type
    if not isinstance(config["name"], str):
        raise ConfigError("`name` must be a string")

    if not isinstance(config["channel"], int):
        raise ConfigError("'channel' must be an integer")

    if not isinstance(config["message"], int):
        raise ConfigError("'message' must be an integer")

    # Check if the color is a hex color string
    if not isinstance(config["color"], str) or not config["color"].startswith("#"):
        raise ConfigError("'color' must be a hex color string")

    if "timestamp" in config:
        # Timestamp must be a string
        if not isinstance(config["timestamp"], str):
            raise ConfigError("'timestamp' must be a string")

        # Check if the timestamp is a valid ISO 8601 string
        try: datetime.fromisoformat(config["timestamp"])
        except ValueError:
            raise ConfigError("'timestamp' must be a valid ISO 8601 string")

    if "fields" in config:
        if not isinstance(config["fields"], list):
            raise ConfigError("'fields' must be a list of dictionaries")

        for field in config["fields"]:
            if not isinstance(field, dict):
                raise ConfigError("'fields' must be a list of dictionaries")

            field_keys = ["name", "value", "inline"]
            try:
                await check_keys(field, field_keys)
            except ConfigError as e:
                raise ConfigError(f"'fields' section error: {e}")

            if not isinstance(field["inline"], bool):
                raise ConfigError(f"'inline' for field '{field['name']}' must be a boolean")

    if "reaction_roles" in config:
        if not isinstance(config["reaction_roles"], list):
            raise ConfigError("`reaction_roles` must be a list")

        for role in config["reaction_roles"]:
            try:
                await check_keys(role, ["emoji", "role", "unique"])
            except ConfigError as e:
                raise ConfigError(f"`reaction_roles` > `{role}` error: {e}")

            if not isinstance(role["role"], int):
                raise ConfigError(f"`reaction_roles` > `{role}` role must be an integer")

            if not isinstance(role["unique"], bool):
                raise ConfigError(f"`reaction_roles` > `{role}` unique must be an boolean")

    return True

async def default_config() -> dict:
    return {
            "name": "",
            "channel": "",
            "message": "",

            "title_text": "Example Embed",
            "title_url": "",

            "author_name": "Example Author",
            "author_url": "",
            "author_icon": "",

            "description": "Example Description",
            "thumbnail": "https://placedog.net/250/250/?id=17",
            "image": "https://placedog.net/500/500/?id=19",

            "color": "#00FF00",

            "fields": [
                {
                    "name": "Example Field",
                    "value": "This is a velue for a field",
                    "inline": False
                }
            ],

            "footer_icon": "https://placedog.net/500/500/?id=19",
            "footer_text": "This is footer text",
            "timestamp": "2025-01-01T00:00:00",

            "reaction_roles":[
                {
                    "emoji": "",
                    "role": "",
                    "unique": True
                }
            ]
    }

async def create_reaction_role(emoji: str, role: int, unique: bool) -> dict:
    return {
        "emoji": emoji,
        "role": role,
        "unique": unique
    }

async def create_embed(config: dict) -> discord.Embed:
    # We have to set the color manually
    if "color" in config:
        # Convert the color to an integer
        embed = discord.Embed(color=await get_color(config["color"]))
    else:
        # Default color
        embed = discord.Embed()

    # Set the title
    if "title_text" in config: embed.title = config["title_text"]
    if "title_url" in config: embed.url = config["title_url"]

    # Author section
    author_name, author_url, author_icon = "", "", ""
    if "author_name" in config:
        author_name = config["author_name"]

    if "author_url" in config:
        author_url = config["author_url"]

    if "author_icon" in config:
        author_icon = config["author_icon"]

    embed.set_author(name=author_name, url=author_url, icon_url=author_icon)

    # Main embed section
    if "description" in config: embed.description = config["description"]
    if "thumbnail" in config: embed.set_thumbnail(url=config["thumbnail"])
    if "image" in config: embed.set_image(url=config["image"])

    # Timestamp, we have to convert it to a datetime object
    if "timestamp" in config:
        timestamp = datetime.fromisoformat(config["timestamp"])
        embed.timestamp = timestamp

    # Footer section
    footer_text, footer_icon = "", ""
    if "footer_text" in config: footer_text = config["footer_text"]
    if "footer_icon" in config: footer_icon = config["footer_icon"]
    embed.set_footer(text=footer_text, icon_url=footer_icon)

    # Additional fields
    if "fields" in config:
        for field in config["fields"]:
            embed.add_field(name=field["name"], value=field["value"], inline=field["inline"])

    return embed