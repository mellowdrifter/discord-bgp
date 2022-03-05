#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import bgpstuff
import discord
import logging
from typing import List
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
ALERTKEY = "%"

COMMANDS = ["route", "origin", "aspath", "roa",
            "asname", "invalids", "totals", "sourced"]

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s: %(levelname)s: %(message)s')


async def send_help(channel):
    return await channel.send(quote("""
bgpstuff.net help.

Commands:
  % route - Returns the active RIB entry for the passed in IP address
  % origin - Returns the origin AS number for the pass in IP address
  % aspath - Returns the AS path I see to get to the passed in IP address
  % roa - Returns the ROA status of the passed in IP address
  % asname - Returns the AS name from the passed in AS number
  % invalids - Returns all RPKI invalid prefixes advertised from the passed in AS number
  % vrps - Returns all Validated ROA Payloads for the passed in AS number
  % sourced - Returns all prefixes originated from the passed in AS number
  % totals - Returns the current IPv4 and IPv6 active prefix count
"""))


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


def quote(txt: str) -> str:
    return f"```{txt}```"


def split_text_green_quote(txt: str) -> List[str]:
    splittxt = txt.split("\n")
    rejoined = ['\n'.join(splittxt[i:i+80])
                for i in range(0, len(splittxt), 80)]
    newtxt = []
    for i in range(len(rejoined)):
        if i == 0:
            newtxt.append(green_quote(rejoined[i]))
        else:
            newtxt.append(quote(rejoined[i]))
    return newtxt


def totals(bgp) -> str:
    try:
        bgp.get_totals()
    except Exception as e:
        return red_quote(e)
    if bgp.status_code != 200:
        return no_200(bgp.status_code)
    return green_quote(f"I see {bgp.total_v4} IPv4 and {bgp.total_v6} IPv6 prefixes active")


def route(prefix: str, bgp) -> str:
    logging.info(f"route request for {prefix}")
    try:
        bgp.get_route(prefix)
    except ValueError as ve:
        return red_quote(ve)
    except Exception as e:
        logging.debug(e)
    if bgp.status_code != 200:
        return no_200(bgp.status_code)
    if not bgp.exists:
        return yellow_quote(f"No prefix exists for {prefix}")
    return green_quote(f"The route for {prefix} is {bgp.route}")


def origin(prefix: str, bgp) -> str:
    logging.info(f"origin request for {prefix}")
    try:
        bgp.get_origin(prefix)
    except ValueError as ve:
        return red_quote(ve)
    except Exception as e:
        logging.debug(e)
        return
    if bgp.status_code != 200:
        return no_200(bgp.status_code)
    if not bgp.exists:
        return yellow_quote(f"No prefix exists for {prefix}")
    return green_quote(f"The origin AS for {prefix} is AS{bgp.origin}")


def aspath(prefix: str, bgp) -> str:
    logging.info(f"aspath request for {prefix}")
    try:
        bgp.get_as_path(prefix)
    except ValueError as ve:
        return red_quote(ve)
    except Exception as e:
        logging.debug(e)
        return
    if bgp.status_code != 200:
        return no_200(bgp.status_code)
    if not bgp.exists:
        return yellow_quote(f"No prefix exists for {prefix}")
    path = " ".join(map(str, bgp.as_path))
    return green_quote(f"The AS path for {prefix} is {path}")


def roa(prefix: str, bgp) -> str:
    logging.info(f"roa request for {prefix}")
    try:
        bgp.get_roa(prefix)
    except ValueError as ve:
        return red_quote(ve)
    except Exception as e:
        logging.debug(e)
        return
    if bgp.status_code != 200:
        return no_200(bgp.status_code)
    if not bgp.exists:
        return yellow_quote(f"No prefix exists for {prefix}")

    status = bgp.roa
    if status == "UNKNOWN":
        status = "UNKNOWN (NO ROA)"
    return green_quote(f"The ROA status for {prefix} is {status}")


def asname(asnum: int, bgp) -> str:
    try:
        num = int(asnum)
    except ValueError:
        return red_quote(f"{asnum} is not an integer")
    try:
        bgp.get_as_name(int(asnum))
    except ValueError as ve:
        return red_quote(ve)
    except Exception as e:
        logging.debug(e)
        return
    if bgp.status_code != 200:
        return no_200(bgp.status_code)
    if not bgp.exists:
        return yellow_quote(f"No AS name exists for {asnum}")
    return green_quote(f"The AS name for {asnum} is {bgp.as_name}")


def invalids(asnum: int, bgp) -> str:
    # TODO: do i need to get them all?
    # TODO: keep a map or something?
    bgp.get_invalids()
    if bgp.status_code != 200:
        return no_200()
    return (f"{bgp.invalids(int(asnum))}")


def sourced(asnum: int, bgp) -> str:
    try:
        num = int(asnum)
    except ValueError:
        return red_quote(f"{asnum} is not an integer")
    try:
        bgp.get_sourced_prefixes(num)
    except ValueError as ve:
        return red_quote(ve)
    except Exception as e:
        logging.debug(e)
        return
    if bgp.status_code != 200:
        return no_200(bgp.status_code)
    if not bgp.exists:
        return yellow_quote(f"AS{asnum} is not sourcing any prefixes")
    prefixes = "\n\t".join(map(str, bgp.sourced))
    return split_text_green_quote(f"AS{asnum} is sourcing the following prefixes:\n\t{prefixes}")


if __name__ == "__main__":
    dis = discord.Client()
    bgp = bgpstuff.Client()

    @ dis.event
    async def on_ready():
        print(f'{dis.user} has connected to Discord!')

    @ dis.event
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
            await send_help(message.channel)
            return

        # Only respond to approved commands
        if request[0].lower() not in COMMANDS:
            return

        if request[0].lower() == "route":
            req = route(request[1], bgp)
            if req == "":
                return
            logging.info(req)
            await message.channel.send(req)
            return

        elif request[0].lower() == "origin":
            req = origin(request[1], bgp)
            if req == "":
                return
            logging.info(req)
            await message.channel.send(req)
            return

        elif request[0].lower() == "aspath":
            req = aspath(request[1], bgp)
            if req == "":
                return
            logging.info(req)
            await message.channel.send(req)
            return

        elif request[0].lower() == "roa":
            req = roa(request[1], bgp)
            if req == "":
                return
            logging.info(req)
            await message.channel.send(req)
            return

        elif request[0].lower() == "asname":
            req = asname(request[1], bgp)
            if req == "":
                return
            logging.info(req)
            await message.channel.send(req)
            return

        elif request[0].lower() == "invalids":
            req = invalids(request[1])
            if req == "":
                return
            logging.info(req)
            await message.channel.send(req)
            return

        elif request[0].lower() == "sourced":
            req = sourced(request[1], bgp)
            if req == "":
                return
            logging.info(req)
            if type(req) == list:
                for msg in req:
                    await message.channel.send(msg)
            else:
                await message.channel.send(req)
            return

        elif request[0].lower() == "totals":
            req = totals(bgp)
            if req == "":
                return
            logging.info(req)
            await message.channel.send(req)
            return

        else:
            await send_help(message.channel)

    dis.run(TOKEN)
