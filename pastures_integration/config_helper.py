import json
import logging
from dataclasses import dataclass, field, asdict

log = logging.getLogger("red.mednis-cogs.pastures_integration")


class ConfigError(Exception):
    pass


@dataclass
class EmbedConfig:
    channel_id: int = 0
    message_id: int = 0
    title: str = "Example Server Title"
    description: str = "**Example Server Description**\nPlayers:`$pcur/$pmax` \nRandom message:`$messages` \n**Server lookup live info** *(if enabled)*:\nServer MOTD:`$motd`\nServer Version:`$version`"
    image: str = "https://file.mednis.network/static_assets/main-logo-mini.png"
    messages: list = field(default_factory=list)
    show_ip: bool = False
    request_status: bool = False
    public_ip: str = ""
    color: int = 0x00FF00

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_json(cls, json_str: str) -> "EmbedConfig":
        try:
            data = json.loads(json_str)
            return cls(**data)
        except Exception as e:
            log.error(f"Failed to parse JSON data in EmbedConfig: {e}")
            raise ConfigError("Invalid JSON for EmbedConfig.")


@dataclass
class ServerConfig:
    one_click_whitelist: bool = False
    one_click_emoji: str = "👍"
    embed: EmbedConfig = field(default_factory=EmbedConfig)
    whitelisted: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return json.dumps(self.to_dict(), indent=4)

    @classmethod
    def from_json(cls, config: dict) -> "ServerConfig":
        log.debug(f"Loading JSON data: {config}")
        try:
            embed_data = config.get("embed", {})
            embed = EmbedConfig(**embed_data) if isinstance(embed_data, dict) else EmbedConfig()
            return cls(embed=embed, **{k: v for k, v in config.items() if k != "embed"})
        except Exception as e:
            log.error(f"Failed to parse JSON data in ServerConfig: {e}")
            raise ConfigError("Invalid JSON for ServerConfig.")

    @classmethod
    def default_config(cls) -> "ServerConfig":
        return cls()

def clear_ids(config: dict):
    config = ServerConfig.from_json(config)
    config.embed.channel_id = 0
    config.embed.message_id = 0
    return config.to_json()
