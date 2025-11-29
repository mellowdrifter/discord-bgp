#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import bgpstuff
import bogons
import discord
import logging
from discord.ext import commands
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

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)

# Initialize Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=ALERTKEY, intents=intents, help_command=None)
bgp_client = bgpstuff.Client()

def no_200(status_code: int) -> str:
    # TODO: this is wrong...
    return "unable to query bgpstuff.net api"

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

@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")

@bot.event
async def on_message(message):
    # bot should not respond to its own message
    if message.author == bot.user:
        return

    # If the message is exactly the alert key, send help
    if message.content.strip() == ALERTKEY:
        await help_command(await bot.get_context(message))
        return

    await bot.process_commands(message)

@bot.command(name="help")
async def help_command(ctx):
    """bgpstuff.net help."""
    await ctx.send(
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

@cached(cache=TTLCache(maxsize=1, ttl=FIVE_MINUTES))
def get_totals(bgp) -> str:
    try:
        bgp.get_totals()
    except Exception as e:
        return red_quote(e)
    if bgp.status_code != 200:
        return no_200(bgp.status_code)
    return green_quote(
        f"I see {bgp.total_v4} IPv4 and {bgp.total_v6} IPv6 prefixes active"
    )

def clean_msg(msg):
    if isinstance(msg, list):
        return [clean_msg(m) for m in msg]
    return msg.replace("```🟢 ", "").replace("```🟡 ", "").replace("```🔴 ", "").replace("```", "").strip()

@bot.command(name="totals")
async def totals_command(ctx):
    """Returns the current IPv4 and IPv6 active prefix count"""
    req = get_totals(bgp_client)
    if req:
        logging.info(clean_msg(req))
        await ctx.send(req)

@cached(cache=TTLCache(maxsize=20, ttl=ONE_MINUTE))
def get_route(prefix: str, bgp) -> str:
    logging.info(f"route request for {prefix}")
    try:
        logging.info("reaching out to API")
        bgp.get_route(prefix)
    except ValueError as ve:
        return red_quote(ve)
    except Exception as e:
        logging.debug(e)
        return
    if bgp.status_code != 200:
        return no_200(bgp.status_code)
    if not bgp.exists:
        return yellow_quote(f"No prefix exists for {prefix}")
    return green_quote(f"The route for {prefix} is {bgp.route}")

@bot.command(name="route")
async def route_command(ctx, prefix: str):
    """Returns the active RIB entry for the passed in IP address"""
    req = get_route(prefix, bgp_client)
    if req:
        logging.info(clean_msg(req))
        await ctx.send(req)

@cached(cache=TTLCache(maxsize=20, ttl=ONE_MINUTE))
def get_origin(prefix: str, bgp) -> str:
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

@bot.command(name="origin")
async def origin_command(ctx, prefix: str):
    """Returns the origin AS number for the passed in IP address"""
    req = get_origin(prefix, bgp_client)
    if req:
        logging.info(clean_msg(req))
        await ctx.send(req)

@cached(cache=TTLCache(maxsize=50, ttl=ONE_HOUR))
def get_geoip(prefix: str, bgp) -> str:
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

@bot.command(name="geoip")
async def geoip_command(ctx, prefix: str):
    """Returns a guesstimate of where the IP is geo located"""
    req = get_geoip(prefix, bgp_client)
    if req:
        logging.info(clean_msg(req))
        await ctx.send(req)

@cached(cache=TTLCache(maxsize=20, ttl=ONE_MINUTE))
def get_aspath(prefix: str, bgp) -> str:
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

@bot.command(name="aspath")
async def aspath_command(ctx, prefix: str):
    """Returns the AS path I see to get to the passed in IP address"""
    req = get_aspath(prefix, bgp_client)
    if req:
        logging.info(clean_msg(req))
        await ctx.send(req)

@cached(cache=TTLCache(maxsize=20, ttl=FIVE_MINUTES))
def get_roa(prefix: str, bgp) -> str:
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

@bot.command(name="roa")
async def roa_command(ctx, prefix: str):
    """Returns the ROA status of the passed in IP address"""
    req = get_roa(prefix, bgp_client)
    if req:
        logging.info(clean_msg(req))
        await ctx.send(req)

@cached(cache=TTLCache(maxsize=50, ttl=ONE_HOUR))
def get_asname(asnum: int, bgp) -> str:
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

@bot.command(name="asname")
async def asname_command(ctx, asnum: str):
    """Returns the AS name from the passed in AS number"""
    req = get_asname(asnum, bgp_client)
    if req:
        logging.info(clean_msg(req))
        await ctx.send(req)

@cached(cache=TTLCache(maxsize=1, ttl=TWENTY_FOUR_HOURS))
def get_asnames(bgp) -> Dict:
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
def get_invalids(asnum: int, bgp) -> str:
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

@bot.command(name="invalids")
async def invalids_command(ctx, asnum: str):
    """Returns all RPKI invalid prefixes advertised from the passed in AS number"""
    req = get_invalids(asnum, bgp_client)
    if req:
        logging.info(clean_msg(req))
        if isinstance(req, list):
            for msg in req:
                await ctx.send(msg)
        else:
            await ctx.send(req)

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
def get_vrps(asnum: int, bgp) -> str:
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

@bot.command(name="vrps")
async def vrps_command(ctx, asnum: str):
    """Returns all Validated ROA Payloads for the passed in AS number"""
    req = get_vrps(asnum, bgp_client)
    if req:
        logging.info(clean_msg(req))
        if isinstance(req, list):
            for msg in req:
                await ctx.send(msg)
        else:
            await ctx.send(req)

@cached(cache=TTLCache(maxsize=20, ttl=ONE_MINUTE))
def get_sourced(asnum: int, bgp) -> str:
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

@bot.command(name="sourced")
async def sourced_command(ctx, asnum: str):
    """Returns all prefixes originated from the passed in AS number"""
    req = get_sourced(asnum, bgp_client)
    if req:
        logging.info(clean_msg(req))
        if isinstance(req, list):
            for msg in req:
                await ctx.send(msg)
        else:
            await ctx.send(req)

if __name__ == "__main__":
    bot.run(TOKEN)
