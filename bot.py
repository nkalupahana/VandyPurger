import base64
import os
import re
from datetime import datetime, timedelta

import asyncio
import discord
import gspread
import json
from discord.ext import commands, tasks
from oauth2client.service_account import ServiceAccountCredentials

bot = commands.Bot(command_prefix="v;")

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]
creds_string = json.loads(base64.b64decode(os.environ["GOOGLE_API_CREDS"] + "==="))

with open("gcreds.json", "w") as fp:
    json.dump(creds_string, fp)
creds = ServiceAccountCredentials.from_json_keyfile_name("gcreds.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Data").sheet1

target_channel_id = [702296171829264394, 781003806740971580]  # wellness-office in vandy discords
purged = [0 for _ in target_channel_id]
# target_channel_id = 722609125950750771 # testing
activity = True


def ope_count(message):
    # updates ope count in sheet
    sheet = client.open("Data").sheet1
    data = sheet.get_all_records()
    author_found = False
    author_count = 0
    new_index = 2
    for record in data:
        if message.author.id == record["id"]:
            author_found = True
            sheet.update_cell(record["index"] + 1, 2, record["number"] + 1)
            author_count = record["number"] + 1
        new_index += 1
    if not author_found:
        new_row = [str(message.author.id), 1, new_index - 1]
        sheet.insert_row(new_row, new_index)
        author_count = 1

    return author_count


@bot.event
async def on_message(message):
    if not message.author.bot:
        match = re.search(r"\bope\b", message.content.lower())
        if match:
            print(message.author)
            count = ope_count(message)
            await message.channel.send(f"{message.author.display_name} has said " f"Ope {count} times. Yikes.")
        # handle chloe 0pe
        elif message.author.id == 495663643485143061 and re.search(r"\b0pe\b", message.content.lower()):
            await message.channel.send("lmao chloe. yIKeS.")
    #         # diya rocks
    #         if message.author.id == 607733264022765568:
    #             await message.add_reaction('<:diyarocks:747953745278533725>')
    await bot.process_commands(message)


@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(name="the clock.", type=3))
    print(f"{bot.user.name} is running...")


def time_to_sleep():
    now = datetime.utcnow()
    # 10am UTC is 5am Vandy time
    remaining_seconds = (
        timedelta(hours=24) - (now - now.replace(hour=10, minute=0, second=0, microsecond=0))
    ).total_seconds() % (24 * 3600)
    remaining = round(remaining_seconds)
    return remaining


@tasks.loop(minutes=30)
async def daily_purge():
    global purged
    for i in range(len(purged)):
        if purged[i] == 1:
            continue
        purge_channel = bot.get_channel(target_channel_id[i])
        messages = await purge_channel.history(limit=1).flatten()
        last_message_time = messages[0].created_at

        diff = datetime.utcnow() - last_message_time
        print(diff)

        if diff > timedelta(minutes=30):
            await purge_channel.send(f"Messages about to be purged in `10` seconds in channel {purge_channel.mention}")
            print("About to yeet.")
            await asyncio.sleep(10)
            deleted = await purge_channel.purge(limit=None)
            await purge_channel.send(f"Yeeted {len(deleted)} messages.")

            remaining = time_to_sleep()
            await purge_channel.send(f"Going to sleep for {remaining} seconds.")

            purged[i] = 1  # set purge flag for specific channel
        else:
            print("Purge snoozed for 30 minutes")

    if sum(purged) == len(purged):  # all purged
        purged = [0 for _ in range(len(purged))]  # reset
        remaining = time_to_sleep()
        print(f"Going to sleep for {remaining} seconds.")
        await asyncio.sleep(remaining)


@daily_purge.before_loop
async def before():
    await bot.wait_until_ready()
    print("Finished waiting")
    remaining = time_to_sleep()
    print(f"Going to sleep for {remaining} seconds.")
    await asyncio.sleep(remaining)


daily_purge.start()


@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {bot.latency * 1000:.03f}ms")


@bot.command()
async def github(ctx):
    await ctx.send("Catch! https://github.com/aadibajpai/VandyPurger")


bot.run(os.environ["DISCORD_TOKEN"])
