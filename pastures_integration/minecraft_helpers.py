import asyncio
import logging
import aiomcrcon
from mcstatus import JavaServer

import mojang

log = logging.getLogger("red.mednis-cogs.pastures_integration")

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
    api = mojang.API()
    try:
        uuid = api.get_uuid(input)
        if not uuid:
            raise RuntimeError(f"Could not find user `{input}` from mojang!")
        return api.get_username(uuid)
    except mojang.errors.MojangError as err:
        logging.error(f"Error occurred while trying to resolve the username `{input}`: {err}")
        if "HTTP 429" in str(err):
            raise RuntimeError("Mojang API rate limit reached! \n Cool it down and try again in a bit..")
        elif "HTTP 404" in str(err):
            raise RuntimeError(f"Could not find user `{input}`. \n Either the username does not exist or you misstyped it.")
        else:
            raise RuntimeError(f"Mojang API call failed to find `{input}`. \n A unknwon error occoured.")

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
        players_raw = response_string.split(":", 1)[1]

        players = players_raw.split(",")  # Split each player into own array element
        w_players = [player.strip(' ') for player in players]  # Strip spaces from names

    else:
        w_players = ["None"]

    return {
        "count": w_number,
        "names": w_players
    }


# Function to check if player has been whitelisted/un-whitelisted successfully!
async def whitelist_success(response_string: str):
    if response_string.startswith("Added"):
        return True
    else:
        if response_string.startswith("Player"):
            raise RuntimeError(f"Player %s is already whitelised!")
        elif response_string.startswith("That player does not exist"):
            raise RuntimeError(f"Player %s does not exist!")


async def whitelist_remove_success(response_string: str):
    if response_string.startswith("Removed"):
        return True
    else:
        if response_string.startswith("Player"):
            raise RuntimeError(f"Player %s is not whitelised!")
        elif response_string.startswith("That player does not exist"):
            raise RuntimeError(f"Player %s does not exist!")



# Async Wrapper Function
async def run_rcon_command(ip: str, key: str, command: str):
    client = aiomcrcon.Client(ip, 25575, key)

    try:
        await client.connect()
    except (aiomcrcon.RCONConnectionError, aiomcrcon.IncorrectPasswordError):
        raise RuntimeError("Error connecting to server!")
    except asyncio.TimeoutError:
        raise RuntimeError("Network/Server timeout! (Response took >2 seconds)")

    try:
        response = await client.send_cmd(command)

    except aiomcrcon.ClientNotConnectedError:
        raise RuntimeError("Error connecting to server!")
    except asyncio.TimeoutError:
        raise RuntimeError("Network/Server timeout! (Response took >2 seconds)")

    await client.close()
    return response[0]

async def lookup_server(ip: str):
    server = JavaServer.lookup(ip)
    try:
        status = await server.async_status()
        return status
    except:
        raise RuntimeError("Server status failed. Not reachable or offline!")