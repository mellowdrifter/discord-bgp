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
    # TODO: this is wrong...r
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

from dataclasses import dataclass

@dataclass
class BotResponse:
    text: str
    type: str = "green"

@cached(cache=TTLCache(maxsize=1, ttl=FIVE_MINUTES))
def get_totals(bgp) -> BotResponse:
    try:
        bgp.get_totals()
    except Exception as e:
        return BotResponse(str(e), "red")
    if bgp.status_code != 200:
        return BotResponse(no_200(bgp.status_code), "plain")
    return BotResponse(
        f"I see {bgp.total_v4} IPv4 and {bgp.total_v6} IPv6 prefixes active", "green"
    )

@cached(cache=TTLCache(maxsize=20, ttl=ONE_MINUTE))
def get_route(prefix: str, bgp) -> BotResponse:
    logging.info(f"route request for {prefix}")
    try:
        logging.info("reaching out to API")
        bgp.get_route(prefix)
    except ValueError as ve:
        return BotResponse(str(ve), "red")
    except Exception as e:
        logging.debug(e)
        return
    if bgp.status_code != 200:
        return BotResponse(no_200(bgp.status_code), "plain")
    if not bgp.exists:
        return BotResponse(f"No prefix exists for {prefix}", "yellow")
    return BotResponse(f"The route for {prefix} is {bgp.route}", "green")

@cached(cache=TTLCache(maxsize=20, ttl=ONE_MINUTE))
def get_origin(prefix: str, bgp) -> BotResponse:
    logging.info(f"origin request for {prefix}")
    try:
        bgp.get_origin(prefix)
    except ValueError as ve:
        return BotResponse(str(ve), "red")
    except Exception as e:
        logging.debug(e)
        return
    if bgp.status_code != 200:
        return BotResponse(no_200(bgp.status_code), "plain")
    if not bgp.exists:
        return BotResponse(f"No prefix exists for {prefix}", "yellow")
    return BotResponse(f"The origin AS for {prefix} is AS{bgp.origin}", "green")

@cached(cache=TTLCache(maxsize=50, ttl=ONE_HOUR))
def get_geoip(prefix: str, bgp) -> BotResponse:
    logging.info(f"geoip request for {prefix}")
    try:
        bgp.get_geoip(prefix)
    except ValueError as ve:
        return BotResponse(str(ve), "red")
    except Exception as e:
        logging.debug(e)
        return
    if bgp.status_code != 200:
        return BotResponse(no_200(bgp.status_code), "plain")
    if not bgp.exists:
        return BotResponse(f"No prefix exists for {prefix}", "yellow")
    city = bgp.geoip["City"]
    country = bgp.geoip["Country"]
    return BotResponse(f"{prefix} might be located in {city}, {country}", "green")

@cached(cache=TTLCache(maxsize=20, ttl=ONE_MINUTE))
def get_aspath(prefix: str, bgp) -> BotResponse:
    logging.info(f"aspath request for {prefix}")
    try:
        bgp.get_as_path(prefix)
    except ValueError as ve:
        return BotResponse(str(ve), "red")
    except Exception as e:
        logging.debug(e)
        return
    if bgp.status_code != 200:
        return BotResponse(no_200(bgp.status_code), "plain")
    if not bgp.exists:
        return BotResponse(f"No prefix exists for {prefix}", "yellow")
    path = " ".join(map(str, bgp.as_path))
    return BotResponse(f"The AS path for {prefix} is {path}", "green")

@cached(cache=TTLCache(maxsize=20, ttl=FIVE_MINUTES))
def get_roa(prefix: str, bgp) -> BotResponse:
    logging.info(f"roa request for {prefix}")
    try:
        bgp.get_roa(prefix)
    except ValueError as ve:
        return BotResponse(str(ve), "red")
    except Exception as e:
        logging.debug(e)
        return
    if bgp.status_code != 200:
        return BotResponse(no_200(bgp.status_code), "plain")
    if not bgp.exists:
        return BotResponse(f"No prefix exists for {prefix}", "yellow")

    status = bgp.roa
    if status == "UNKNOWN":
        status = "UNKNOWN (NO ROA)"
    return BotResponse(f"The ROA status for {prefix} is {status}", "green")

@cached(cache=TTLCache(maxsize=50, ttl=ONE_HOUR))
def get_asname(asnum: int, bgp) -> BotResponse:
    logging.info(f"asname request for {asnum}")
    try:
        num = int(asnum)
    except ValueError:
        return BotResponse(f"{asnum} is not an integer", "red")

    if not bogons.valid_public_asn(num):
        return BotResponse(f"{asnum} is not a valid ASN", "red")
    
    try:
        name = bgp.get_as_name(num)
    except ValueError as ve:
        return BotResponse(str(ve), "red")
    except Exception as e:
        logging.debug(e)
        return
    
    if not bgp.exists:
        return BotResponse(f"No AS name exists for {asnum}", "yellow")

    return BotResponse(f"The AS name for {num} is {bgp.as_name}", "green")

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
def get_invalids(asnum: int, bgp) -> BotResponse:
    try:
        num = int(asnum)
    except ValueError:
        return BotResponse(f"{asnum} is not an integer", "red")

    if not bogons.valid_public_asn(num):
        return BotResponse(f"{asnum} is not a valid ASN", "red")

    invalids = all_invalids(bgp)
    if num in invalids:
        prefixes = "\n\t".join(map(str, invalids[num]))
        return BotResponse(
            f"AS{asnum} is originating the following invalid prefixes:\n\t{prefixes}",
            "yellow",
        )
    else:
        return BotResponse(f"AS{num} is not originating any invalid prefixes", "green")

@cached(cache=TTLCache(maxsize=20, ttl=FIVE_MINUTES))
def get_vrps(asnum: int, bgp) -> BotResponse:
    try:
        num = int(asnum)
    except ValueError:
        return BotResponse(f"{asnum} is not an integer", "red")

    try:
        vrps = bgp.get_vrps(num)
    except ValueError as ve:
        return BotResponse(str(ve), "red")
    except Exception as e:
        logging.debug(e)
        return
    if bgp.status_code != 200:
        return BotResponse(no_200(bgp.status_code), "plain")
    if not bgp.vrps:
        return BotResponse(f"AS{num} has no VRPs", "yellow")
    vrps = "\n\t".join(map(str, bgp.vrps))
    return BotResponse(f"AS{asnum} has the following VRPs:\n\t{vrps}", "green")

@cached(cache=TTLCache(maxsize=20, ttl=ONE_MINUTE))
def get_sourced(asnum: int, bgp) -> BotResponse:
    try:
        num = int(asnum)
    except ValueError:
        return BotResponse(f"{asnum} is not an integer", "red")

    try:
        bgp.get_sourced_prefixes(num)
    except ValueError as ve:
        return BotResponse(str(ve), "red")
    except Exception as e:
        logging.debug(e)
        return
    if bgp.status_code != 200:
        return BotResponse(no_200(bgp.status_code), "plain")
    if not bgp.exists:
        return BotResponse(f"AS{asnum} is not sourcing any prefixes", "yellow")
    prefixes = "\n\t".join(map(str, bgp.sourced))
    return BotResponse(
        f"AS{asnum} is sourcing the following prefixes:\n\t{prefixes}", "green"
    )

async def send_response(ctx, response: BotResponse):
    if not response:
        return

    logging.info(response.text)

    # Format the response
    if response.type == "green":
        formatted_text = green_quote(response.text)
    elif response.type == "yellow":
        formatted_text = yellow_quote(response.text)
    elif response.type == "red":
        formatted_text = red_quote(response.text)
    else:
        formatted_text = quote(response.text)

    # Split if too long (simple split for now, mirroring original logic if needed)
    # The original logic had specific split functions for green/yellow quotes.
    # We can generalize this.
    
    if len(formatted_text) > 2000: # Discord limit is 2000
         # Re-implement splitting logic if needed, but for now let's stick to the original logic's intent
         # The original split logic was very specific to list of lines.
         # Let's adapt the split logic here.
         splittxt = response.text.split("\n")
         rejoined = ["\n".join(splittxt[i : i + 80]) for i in range(0, len(splittxt), 80)]
         
         for i in range(len(rejoined)):
             chunk = rejoined[i]
             if i == 0:
                 if response.type == "green":
                     await ctx.send(green_quote(chunk))
                 elif response.type == "yellow":
                     await ctx.send(yellow_quote(chunk))
                 elif response.type == "red":
                     await ctx.send(red_quote(chunk))
                 else:
                     await ctx.send(quote(chunk))
             else:
                 await ctx.send(quote(chunk))
    else:
        await ctx.send(formatted_text)


@bot.command(name="totals")
async def totals_command(ctx):
    """Returns the current IPv4 and IPv6 active prefix count"""
    req = get_totals(bgp_client)
    await send_response(ctx, req)

@bot.command(name="route")
async def route_command(ctx, prefix: str):
    """Returns the active RIB entry for the passed in IP address"""
    req = get_route(prefix, bgp_client)
    await send_response(ctx, req)

@bot.command(name="origin")
async def origin_command(ctx, prefix: str):
    """Returns the origin AS number for the passed in IP address"""
    req = get_origin(prefix, bgp_client)
    await send_response(ctx, req)

@bot.command(name="geoip")
async def geoip_command(ctx, prefix: str):
    """Returns a guesstimate of where the IP is geo located"""
    req = get_geoip(prefix, bgp_client)
    await send_response(ctx, req)

@bot.command(name="aspath")
async def aspath_command(ctx, prefix: str):
    """Returns the AS path I see to get to the passed in IP address"""
    req = get_aspath(prefix, bgp_client)
    await send_response(ctx, req)

@bot.command(name="roa")
async def roa_command(ctx, prefix: str):
    """Returns the ROA status of the passed in IP address"""
    req = get_roa(prefix, bgp_client)
    await send_response(ctx, req)

@bot.command(name="asname")
async def asname_command(ctx, asnum: str):
    """Returns the AS name from the passed in AS number"""
    req = get_asname(asnum, bgp_client)
    await send_response(ctx, req)

@bot.command(name="invalids")
async def invalids_command(ctx, asnum: str):
    """Returns all RPKI invalid prefixes advertised from the passed in AS number"""
    req = get_invalids(asnum, bgp_client)
    await send_response(ctx, req)

@bot.command(name="vrps")
async def vrps_command(ctx, asnum: str):
    """Returns all Validated ROA Payloads for the passed in AS number"""
    req = get_vrps(asnum, bgp_client)
    await send_response(ctx, req)

@bot.command(name="sourced")
async def sourced_command(ctx, asnum: str):
    """Returns all prefixes originated from the passed in AS number"""
    req = get_sourced(asnum, bgp_client)
    await send_response(ctx, req)

if __name__ == "__main__":
    bot.run(TOKEN)
