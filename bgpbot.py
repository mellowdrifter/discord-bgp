#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import bgpstuff
import discord
from typing import List
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
ALERTKEY = "%"

COMMANDS = ["route", "origin", "aspath", "asname", "invalids", "totals"]


async def send_help(channel):
    print("sending help")
    return await channel.send("You FOOL")


def no_200(status_code: int) -> str:
    # TODO: this is wrong...
    return "unable to query bgpstuff.net api"


def decode_request(req: str) -> List[str]:
    # Remove the alert key, which may or may not have a space after
    return req[1:].split()


def green_quote(txt: str) -> str:
    return f"`🟢 {txt}`"


def yellow_quote(txt: str) -> str:
    return f"`🟡 {txt}`"


def red_quote(txt: str) -> str:
    return f"`🔴 {txt}`"


def totals(bgp) -> str:
    try:
        bgp.get_totals()
    except Exception as e:
        return red_quote(e)
    if bgp.status_code != 200:
        return no_200(bgp.status_code)
    return green_quote(f"I see {bgp.total_v4} IPv4 and {bgp.total_v6} IPv6 prefixes active")


def route(prefix: str, bgp) -> str:
    try:
        bgp.get_route(prefix)
    except ValueError as ve:
        return red_quote(ve)
        # TODO: What about other exceptions?
    if bgp.status_code != 200:
        return no_200(bgp.status_code)
    if not bgp.exists:
        return yellow_quote(f"No prefix exists for {prefix}")
    return green_quote(f"The route for {prefix} is {bgp.route}")


def origin(prefix: str, bgp) -> str:
    try:
        bgp.get_origin(prefix)
    except ValueError as ve:
        return red_quote(ve)
    if bgp.status_code != 200:
        return no_200()
    if not bgp.exists:
        return yellow_quote(f"No prefix exists for {prefix}")
    return green_quote(f"The origin AS for {prefix} is AS{bgp.origin}")


def aspath(prefix: str, bgp) -> str:
    bgp.get_as_path(prefix)
    if bgp.status_code != 200:
        return no_200()
    if not bgp.exists:
        return (f"No prefix exists for {prefix}")
    path = " ".join(map(str, bgp.as_path))
    return (f"The AS path for {prefix} is {path}")


def asname(asnum: int, bgp) -> str:
    # TODO: make sure this is actually an int!
    bgp.get_as_name(int(asnum))
    if bgp.status_code != 200:
        return no_200()
    if not bgp.exists:
        return (f"No ASNAME exists for {asnum}")
    return (f"The AS name for {asnum} is {bgp.as_name}")


def invalids(asnum: int, bgp) -> str:
    # TODO: make sure this is actually an int!
    # TODO: do i need to get them all?
    bgp.get_invalids()
    if bgp.status_code != 200:
        return no_200()
    return (f"{bgp.invalids(int(asnum))}")


if __name__ == "__main__":
    dis = discord.Client()
    bgp = bgpstuff.Client()

    @dis.event
    async def on_ready():
        print(f'{dis.user} has connected to Discord!')

    @dis.event
    async def on_message(message):
        # bot should not respond to its own message
        if message.author == dis.user:
            return

        # Only respond to queries using the alert key
        if not message.content.startswith(ALERTKEY):
            return

        # If there is no query, return help message and return
        request = decode_request(message.content)
        if len(request) == 0:
            print("nothing to do")
            await send_help(message.channel)
            return

        # Only respond to approved commands
        if request[0].lower() not in COMMANDS:
            return

        if request[0].lower() == "route":
            req = route(request[1], bgp)
            print(req)
            await message.channel.send(req)
            return

        elif request[0].lower() == "origin":
            req = origin(request[1], bgp)
            print(req)
            await message.channel.send(req)
            return

        elif request[0].lower() == "aspath":
            req = aspath(request[1])
            print(req)
            await message.channel.send(req)
            return

        elif request[0].lower() == "asname":
            req = asname(request[1])
            print(req)
            await message.channel.send(req)
            return

        elif request[0].lower() == "invalids":
            req = invalids(request[1])
            print(req)
            await message.channel.send(req)
            return

        elif request[0].lower() == "totals":
            req = totals(bgp)
            print(req)
            await message.channel.send(req)
            return

    dis.run(TOKEN)
