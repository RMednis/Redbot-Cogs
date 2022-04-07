from mcrcon import MCRcon
from mcrcon import MCRconException
from mojang import MojangAPI
from mojang.api import MojangError


# Functions for dealing with player data
async def player_count(response_string: str):
    players_split = response_string.split(" ")  # Split the entire response into an array
    online_players_raw = response_string.split("online:", 1)[1]  # Discard useless data

    try:  # Let's try and convert them to ints!
        current_players = int(players_split[2])  # The current player amount will always be number 2
        max_players = int(players_split[7])  # The max player amount will always be number 7
    except ValueError:
        current_players = 0
        max_players = 0

    if current_players > 0:
        players = online_players_raw.split(",")  # Split each player into own array element
        players = [player.strip(' ') for player in players]  # Strip spaces from names

    else:
        players = ["None"]



    return {
        "current": current_players,
        "max": max_players,
        "names": players
    }


# Functions for dealing with username resolution
async def check_name(input: str):
    try:
        uuid = MojangAPI.get_uuid(input)
        if not uuid:
            raise RuntimeError(f"Could not find user `{input}` from mojang!")
        return MojangAPI.get_username(uuid)
    except MojangError:
        raise RuntimeError(f"Error connecting to mojang api!")


async def split_names(input: str):
    input.strip(" ")

    if " " in input:
        data = input.split(" ")
        data.sort(key=len)
        input = data[len(data) - 1]
        input.strip(" ")

    return input


# Function for dealing with existing whitelist data
async def whitelisted_players(response_string: str):
    print(response_string)

    w_number_raw = response_string.split(" ")[2]

    try:
        w_number = int(w_number_raw)
    except ValueError:
        w_number = 0

    if w_number > 0:
        players_raw = response_string.split("players:", 1)[1]

        players = players_raw.split(",")  # Split each player into own array element
        w_players = [player.strip(' ') for player in players]  # Strip spaces from names

    else:
        w_players = ["None"]

    return {
        "count": w_number,
        "names": w_players
    }


# Function to check if player has been whitelisted/un-whitelisted successfully!
async def whitelist_success(response_string:str):
    if response_string.startswith("Added"):
        return True
    else:
        return False


async def whitelist_remove_success(response_string:str):
    if response_string.startswith("Removed"):
        return True
    else:
        return False


# Main RCON Command Execution Function!
async def run_rcon_command(ip: str, key: str, command: str):
    try:
        with MCRcon(ip, key) as rcon:
            try:
                response = rcon.command(command)
                rcon.disconnect()
            except (ConnectionResetError, ConnectionAbortedError):
                raise RuntimeError("Error Connecting to server!")
            return response
    except (ConnectionRefusedError, MCRconException):
        raise RuntimeError("Error Connecting to server!")
