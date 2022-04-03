# Functions for dealing with player data!

async def player_count(response_string):
    players_split = response_string.split(" ")  # Split the entire response into an array

    return {
        "current": players_split[2],  # The current player amount will always be number 2
        "max": players_split[7]  # The max player amount will always be number 7
    }


async def player_online(response_string):
    online_players_raw = response_string.split("online:", 1)[1]  # Discard useless data

    players = online_players_raw.split(",")  # Split each player into own array element
    players = [player.strip(' ') for player in players]  # Strip spaces from names

    return players
