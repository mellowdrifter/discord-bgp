#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import bgpstuff
import bogons
import discord
import logging
from cachetools import cached, TTLCache
from dotenv import load_dotenv
from typing import Dict, List

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
ALERTKEY = "%"
ONE_MINUTE = 60
FIVE_MINUTES = 5 * ONE_MINUTE
ONE_HOUR = 60 * ONE_MINUTE
TWENTY_FOUR_HOURS = 24 * ONE_HOUR

COMMANDS = [
    "route",
    "origin",
    "aspath",
    "roa",
    "help",
    "asname",
    "invalids",
    "totals",
    "sourced",
    "vrps",
    "geoip",
]

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


async def send_help(channel):
    return await channel.send(
        quote(
            """
bgpstuff.net help.

Commands:
  % route - Returns the active RIB entry for the passed in IP address
  % origin - Returns the origin AS number for the passed in IP address
  % aspath - Returns the AS path I see to get to the passed in IP address
  % roa - Returns the ROA status of the passed in IP address
  % asname - Returns the AS name from the passed in AS number
  % geoip - Returns a guesstimate of where the IP is geo located
  % invalids - Returns all RPKI invalid prefixes advertised from the passed in AS number
  % vrps - Returns all Validated ROA Payloads for the passed in AS number
  % sourced - Returns all prefixes originated from the passed in AS number
  % totals - Returns the current IPv4 and IPv6 active prefix count
"""
        )
    )


def no_200(status_code: int) -> str:
    # TODO: this is wrong...
    return "unable to query bgpstuff.net api"


def decode_request(req: str) -> List[str]:
    # Remove the alert key, which may or may not have a space after
    return req[1:].split()


def green_quote(txt: str) -> str:
    return f"```🟢 {txt}```"


def yellow_quote(txt: str) -> str:
    return f"```🟡 {txt}```"


def red_quote(txt: str) -> str:
    return f"```🔴 {txt}```"


def quote(txt: str) -> str:
    return f"```{txt}```"


def split_text_green_quote(txt: str) -> List[str]:
    splittxt = txt.split("\n")
    rejoined = ["\n".join(splittxt[i : i + 80]) for i in range(0, len(splittxt), 80)]
    newtxt = []
    for i in range(len(rejoined)):
        if i == 0:
            newtxt.append(green_quote(rejoined[i]))
        else:
            newtxt.append(quote(rejoined[i]))
    return newtxt


def split_text_yellow_quote(txt: str) -> List[str]:
    splittxt = txt.split("\n")
    rejoined = ["\n".join(splittxt[i : i + 80]) for i in range(0, len(splittxt), 80)]
    newtxt = []
    for i in range(len(rejoined)):
        if i == 0:
            newtxt.append(yellow_quote(rejoined[i]))
        else:
            newtxt.append(quote(rejoined[i]))
    return newtxt


@cached(cache=TTLCache(maxsize=1, ttl=FIVE_MINUTES))
def totals(bgp) -> str:
    try:
        bgp.get_totals()
    except Exception as e:
        return red_quote(e)
    if bgp.status_code != 200:
        return no_200(bgp.status_code)
    return green_quote(
        f"I see {bgp.total_v4} IPv4 and {bgp.total_v6} IPv6 prefixes active"
    )


@cached(cache=TTLCache(maxsize=20, ttl=ONE_MINUTE))
def route(prefix: str, bgp) -> str:
    logging.info(f"route request for {prefix}")
    try:
        logging.info("reaching out to API")
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


@cached(cache=TTLCache(maxsize=20, ttl=ONE_MINUTE))
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


@cached(cache=TTLCache(maxsize=50, ttl=ONE_HOUR))
def geoip(prefix: str, bgp) -> str:
    logging.info(f"geoip request for {prefix}")
    try:
        bgp.get_geoip(prefix)
    except ValueError as ve:
        return red_quote(ve)
    except Exception as e:
        logging.debug(e)
        return
    if bgp.status_code != 200:
        return no_200(bgp.status_code)
    if not bgp.exists:
        return yellow_quote(f"No prefix exists for {prefix}")
    city = bgp.geoip["City"]
    country = bgp.geoip["Country"]
    return green_quote(f"{prefix} might be located in {city}, {country}")


@cached(cache=TTLCache(maxsize=20, ttl=ONE_MINUTE))
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


@cached(cache=TTLCache(maxsize=20, ttl=FIVE_MINUTES))
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


@cached(cache=TTLCache(maxsize=50, ttl=ONE_HOUR))
def asname(asnum: int, bgp) -> str:
    logging.info(f"asname request for {asnum}")
    try:
        num = int(asnum)
    except ValueError:
        return red_quote(f"{asnum} is not an integer")

    if not bogons.valid_public_asn(num):
        return red_quote(f"{asnum} is not a valid ASN")
    
    try:
        name = bgp.get_as_name(num)
    except ValueError as ve:
        return red_quote(ve)
    except Exception as e:
        logging.debug(e)
        return
    
    if not bgp.exists:
        return yellow_quote(f"No AS name exists for {asnum}")

    return green_quote(f"The AS name for {num} is {bgp.as_name}")

@cached(cache=TTLCache(maxsize=1, ttl=TWENTY_FOUR_HOURS))
def asnames(bgp) -> Dict:
    try:
        bgp.get_as_names()
    except Exception as e:
        logging.debug(e)
        return
    if bgp.status_code != 200:
        # TODO: This really the best return?
        logging.debug(bgp.status_code)
        return
    return bgp.all_as_names


@cached(cache=TTLCache(maxsize=20, ttl=FIVE_MINUTES))
def invalids(asnum: int, bgp) -> str:
    try:
        num = int(asnum)
    except ValueError:
        return red_quote(f"{asnum} is not an integer")

    if not bogons.valid_public_asn(num):
        return red_quote(f"{asnum} is not a valid ASN")

    invalids = all_invalids(bgp)
    if num in invalids:
        prefixes = "\n\t".join(map(str, invalids[num]))
        return split_text_yellow_quote(
            f"AS{asnum} is originating the following invalid prefixes:\n\t{prefixes}"
        )
    else:
        return green_quote(f"AS{num} is not originating any invalid prefixes")


@cached(cache=TTLCache(maxsize=1, ttl=ONE_HOUR))
def all_invalids(bgp) -> Dict:
    print("Getting all invalids from API")
    try:
        bgp.get_invalids()
    except Exception as e:
        logging.debug(e)
        return
    if bgp.status_code != 200:
        # TODO: This really the best return?
        logging.debug(bgp.status_code)
        return
    return bgp.all_invalids


@cached(cache=TTLCache(maxsize=20, ttl=FIVE_MINUTES))
def vrps(asnum: int, bgp) -> str:
    try:
        num = int(asnum)
    except ValueError:
        return red_quote(f"{asnum} is not an integer")

    try:
        vrps = bgp.get_vrps(num)
    except ValueError as ve:
        return red_quote(ve)
    except Exception as e:
        logging.debug(e)
        return
    if bgp.status_code != 200:
        return no_200(bgp.status_code)
    if not bgp.vrps:
        return yellow_quote(f"AS{num} has no VRPs")
    vrps = "\n\t".join(map(str, bgp.vrps))
    return split_text_green_quote(f"AS{asnum} has the following VRPs:\n\t{vrps}")


@cached(cache=TTLCache(maxsize=20, ttl=ONE_MINUTE))
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
    return split_text_green_quote(
        f"AS{asnum} is sourcing the following prefixes:\n\t{prefixes}"
    )


def start(dis, bgp):
    @dis.event
    async def on_ready():
        print(f"{dis.user} has connected to Discord!")

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
            await send_help(message.channel)
            return

        # Only respond to approved commands
        if request[0].lower() not in COMMANDS:
            return

        if request[0].lower() == "help":
            await send_help(message.channel)
            return

        if request[0].lower() == "route":
            req = route(request[1], bgp)
            if req == "":
                return
            logging.info(req)
            await message.channel.send(req)
            return

        elif request[0].lower() == "geoip":
            req = geoip(request[1], bgp)
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
            req = invalids(request[1], bgp)
            if req == "":
                return
            logging.info(req)
            if type(req) == list:
                for msg in req:
                    await message.channel.send(msg)
            else:
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

        elif request[0].lower() == "vrps":
            req = vrps(request[1], bgp)
            if req:
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


if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True
    dis = discord.Client(intents=intents)
    bgp = bgpstuff.Client()
    start(dis, bgp)
