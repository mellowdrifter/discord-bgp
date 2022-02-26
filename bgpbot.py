#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import bgpstuff
import discord
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
ALERTKEY = "%"

COMMANDS = ["route", "origin"]


async def send_help(channel):
    print("sending help")
    return await channel.send("You FOOL")


def remove_alert_key(content) -> str:
    return content[1:]


def no_200() -> str:
    return "unable to query bgpstuff.net api"


def route(prefix: str, bgp) -> str:
    bgp.get_route(prefix)
    if bgp.status_code != 200:
        return no_200()
    if not bgp.exists:
        return (f"no prefix exists for {prefix}")
    return (f"the route for {prefix} is {bgp.route}")


if __name__ == "__main__":
    client = discord.Client()
    bgp = bgpstuff.Client()

    @client.event
    async def on_ready():
        print(f'{client.user} has connected to Discord!')

    @client.event
    async def on_message(message):
        # bot should not respond to its own message
        if message.author == client.user:
            return

        # Only respond to queries using the alert key
        if not message.content.startswith(ALERTKEY):
            return

        # Remove the alert key, which may or may not have a space after
        content = remove_alert_key(message.content)

        # If there is no query, return help message and return
        request = content.split()
        if len(request) == 0:
            print("nothing to do")
            await send_help(message.channel)
            return

        # Only respond to approved commands
        if request[0].lower() not in COMMANDS:
            return

        print(f"Tryting to get {request[0]} for {request[1]}")
        req = route(request[1], bgp)
        print(req)

        print(f"{message.author} said {content}")
        await message.channel.send(bgp.route)

    client.run(TOKEN)
