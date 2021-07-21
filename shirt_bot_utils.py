import asyncio
import enum
import json
import os
import re

import aiohttp
import discord
from discord.ext import commands, tasks

from encoder import encoder


# ################################
# ### Bunch of Necessary Stuff ###
# ################################

with open("config.json") as file:
    config = json.load(file)
API_KEY = config["api_key"]
BOT_TOKEN = config["bot_token"]
PREFIX = config["prefix"]

URL_PATTERN = (
    r"(https?:\/\/(?:www\.|(?!www))"
    r"[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|"
    r"www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|"
    r"https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|"
    r"www\.[a-zA-Z0-9]+\.[^\s]{2,})"
)

ENCODER = encoder.get_encoder()
HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {API_KEY}',
}
URL = 'https://api.openai.com/v1/engines/davinci/completions'
TOKEN_LIMIT = 2048
with open("help_text.txt") as file:
    HELP_TEXT = file.read()
matches = re.findall(r"<\{\[(.*)]}>(.+)<\{\[\1/]}>", HELP_TEXT, flags=re.S)
help_categories = {k: v.strip() for k, v in matches}


shirt_queue = asyncio.Queue(maxsize=1)

# ###############################################################
# ### Creating Data Files and Directories if They Don't Exist ###
# ###############################################################

if not os.path.exists("./data"):
    os.mkdir("data")
if not os.path.exists("./data/shirt_talk.txt"):
    open("data/shirt_talk.txt", "w").close()
if not os.path.exists("./data/shirt_reply.txt"):
    open("data/shirt_reply.txt", "w").close()
if not os.path.exists("./data/shirt_random.txt"):
    open("data/shirt_random.txt", "w").close()
if not os.path.exists("./data/uncensored_links.txt"):
    open("data/uncensored_links.txt", "w").close()

with open("data/shirt_talk.txt") as file:
    shirt_talk_channels = {
        int(k.split()[0]): float(k.split()[1])
        for k in file.read().split('\n')
        if k
    }
with open("data/shirt_reply.txt") as file:
    shirt_reply_channels = {
        int(k.split()[0]): float(k.split()[1])
        for k in file.read().split('\n')
        if k
    }
with open("data/shirt_random.txt") as file:
    shirt_random_channels = {
        int(k.split()[0]): tuple(float(x) for x in k.split()[1:])
        for k in file.read().split('\n')
        if k
    }
with open("data/uncensored_links.txt") as file:
    uncensored_link_channels = [int(k) for k in file.read().split('\n') if k]

# #################
# ### Bot Stuff ###
# #################


class ShirtContext(commands.Context):
    """Edited Context that can send a message and apply some filters."""

    async def shirt_send(self, content=None, **kwargs):
        msg = content
        msg = remove_slurs(msg)
        if self.channel.id not in uncensored_link_channels:
            msg = remove_links(msg)
        await self.send(msg[:2000], **kwargs)


class ShirtBot(commands.Bot):
    """The Shirt Bot class"""

    async def get_context(self, message, cls=None):
        return await super().get_context(
            message,
            cls=cls if cls is not None else ShirtContext
        )


def permissions_or_dm(**kwargs):
    """Returns True if a user is in a DM or if they have permissions."""

    async def predicate(ctx):
        return (
            not ctx.guild or
            await commands.has_permissions(**kwargs).predicate(ctx)
        )
    return commands.check(predicate)


def float_nan_converter(argument):
    """Float converter that also checks for NaNs."""

    try:
        argument = float(argument)
        if argument != argument:
            raise ValueError("The provided float is a NaN.")
    except ValueError as e:
        raise commands.BadArgument(
            f'Converting to "float (non-NaN)"'
            f'failed from parameter "{argument}".'
            ) from e
    return argument


# #########################################################
# ### Stuff For Collecting Messages and Sending Prompts ###
# #########################################################


class MessageCollectionType(enum.Enum):
    TRIGGER_OR_SHIRT_RANDOM = 0
    SHIRT_TALK = 1
    SHIRT_REPLYING = 2


async def collect_messages(channel, *, mode, before=None):
    """Collects messages from a channel for Shirt Bot"""

    lst = []
    async for x in channel.history(limit=50, before=before):
        context = await bot.get_context(x)
        if context.valid and context.command.name == "reset":
            break

        if not context.valid:
            author = x.author.name if x.author != bot.user else 'Shirtman'
            if (
                x.content.startswith("# ") and
                mode == MessageCollectionType.SHIRT_TALK
            ):
                lst.append(f"{author}: {x.content[1:].lstrip()}")
            elif (
                mode == MessageCollectionType.TRIGGER_OR_SHIRT_RANDOM or
                (not x.content.startswith("$ ") and x.content != "#")
            ):
                lst.append(f"{author}: {x.content}")

        if len(lst) >= 15:
            break
    lst.reverse()
    return lst


async def send_prompt(
    prompt,
    max_tokens,
    temperature,
    stop=None,
    decrease_max=False,
    first_line=True
):
    """Sends prompt to the OpenAI API."""

    tokens = ENCODER.encode(prompt)
    if len(tokens) > TOKEN_LIMIT-max_tokens and not decrease_tokens:
        tokens = tokens[:TOKEN_LIMIT-max_tokens]
    elif decrease_tokens:
        max_tokens = TOKEN_LIMIT-len(tokens)
    prompt = ENCODER.decode(tokens)

    datadict = {
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "n": 1,
        "stream": False,
        "logprobs": None,
        "presence_penalty": 0.5,
        "frequency_penalty": 0.1
    }
    if stop is not None:
        datadict["stop"] = stop
    data = json.dumps(datadict, separators=(",", ":"))
    async with aiohttp.ClientSession() as session:
        async with session.post(URL, headers=HEADERS, data=data) as response:
            response_text = await response.text()

    result = json.loads(resonse_text)["choices"][0]["text"]
    return result.splitlines()[0] if first_line else result


# #####################################
# ### Tasks For Updating Data Files ###
# #####################################

@tasks.loop()
async def update_data_files():
    """Updates data files."""

    operation, channel_id, randomness, chance = await shirt_queue.get()

    if operation == "SET_SHIRT_TALK":
        shirt_talk_channels[channel_id] = randomness
        file, lst = "shirt_talk", shirt_talk_channels
    elif operation == "UNSET_SHIRT_TALK":
        del shirt_talk_channels[channel_id]
        file, lst = "shirt_talk", shirt_talk_channels
    elif operation == "SET_SHIRT_REPLY":
        shirt_reply_channels[channel_id] = randomness
        file, lst = "shirt_reply", shirt_reply_channels
    elif operation == "UNSET_SHIRT_REPLY":
        del shirt_reply_channels[channel_id]
        file, lst = "shirt_reply", shirt_reply_channels
    elif operation == "SET_SHIRT_RANDOM":
        shirt_random_channels[channel_id] = randomness, chance
        file, lst = "shirt_random", shirt_random_channels
    elif operation == "UNSET_SHIRT_RANDOM":
        del shirt_random_channels[channel_id]
        file, lst = "shirt_random", shirt_random_channels
    elif operation == "UNCENSOR_LINKS":
        uncensored_link_channels.append(channel_id)
        file, lst = "uncensored_links", uncensored_link_channels
    elif operation == "CENSOR_LINKS":
        uncensored_link_channels.remove(channel_id)
        file, lst = "uncensored_links", uncensored_link_channels

    bak = open(f"data/{file}_backup.txt", "w")
    f = open(f"data/{file}.txt", "r+")
    bak.write(f.read())
    bak.close()
    f.seek(0)
    if file == "uncensored_links":
        to_write = '\n'.join(map(str, lst))
    elif file == "shirt_random":
        to_write = '\n'.join([
            f"{k} {' '.join(map(str, v))}" for k, v in lst.items()
        ])
    else:
        to_write = '\n'.join(f"{k} {v}" for k, v in lst.items())
    f.write(to_write)
    f.truncate()
    f.close()

    shirt_queue.task_done()


@tasks.loop(minutes=60)
async def clean_unused_channels():

    await bot.wait_until_ready()

    if update_data_files.is_running():
        update_data_files.stop()
    all_channels = bot.private_channels+list(bot.get_all_channels())
    all_channels = [c.id for c in all_channels]
    for channel in list(shirt_talk_channels):
        if channel not in all_channels:
            del shirt_talk_channels[channel]
    for channel in list(shirt_reply_channels):
        if channel not in all_channels:
            del shirt_reply_channels[channel]
    for channel in list(shirt_random_channels):
        if channel not in all_channels:
            del shirt_random_channels[channel]
    for channel in uncensored_link_channels.copy():
        if channel not in all_channels:
            uncensored_link_channels.remove(channel)

    for file, lst in (
        ("shirt_talk", shirt_talk_channels),
        ("shirt_reply", shirt_reply_channels),
        ("shirt_random", shirt_random_channels),
        ("uncensored_links", uncensored_link_channels)
    ):
        bak = open(f"data/{file}_backup.txt", "w")
        f = open(f"data/{file}.txt", "r+")
        bak.write(f.read())
        bak.close()
        f.seek(0)
        if file == "uncensored_links":
            to_write = '\n'.join(map(str, lst))
        elif file == "shirt_random":
            to_write = '\n'.join([
                f"{k} {' '.join(map(str, v))}" for k, v in lst.items()
            ])
        else:
            to_write = '\n'.join(f"{k} {v}" for k, v in lst.items())
        f.write(to_write)
        f.truncate()
        f.close()

    update_data_files.start()


# ####################
# ### Some Filters ###
# ####################

def remove_links(string):
    """Removes links from a string."""
    return re.sub(URL_PATTERN, '[link removed]', string)


def remove_slurs(string):
    """Removes some slurs from a string."""
    return re.sub(
        "nigger|nigga|faggot|chink|coon|retard|tranny|kike|dyke",
        "[slur removed]",
        string,
        flags=re.I
    )


# ###################
# ### Error Stuff ###
# ###################

async def handle_unset_or_toggle_error(ctx, error):
    error = getattr(error, 'original', error)
    ignored = (commands.TooManyArguments, discord.Forbidden)
    if isinstance(error, ignored):
        pass
    elif isinstance(error, commands.BadArgument):
        with contextlib.suppress(discord.Forbidden):
            await ctx.send("Unknown channel.")
    elif isinstance(error, commands.MissingPermissions):
        with contextlib.suppress(discord.Forbidden):
            await ctx.send(
                "You need to have the `Manage Channels` "
                "permission to execute this command."
            )
    else:
        print(f"Ignoring exception in command {ctx.command}:", file=sys.stderr)
        traceback.print_exception(
            type(error),
            error,
            error.__traceback__,
            file=sys.stderr
        )


async def handle_set_error(ctx, error, arguments):
    error = getattr(error, 'original', error)
    ignored = (commands.TooManyArguments, discord.Forbidden)
    if isinstance(error, ignored):
        pass
    elif isinstance(error, commands.MissingPermissions):
        with contextlib.suppress(discord.Forbidden):
            await ctx.send(
                "You need to have the `Manage Channels` "
                "permission to execute this command."
            )
    elif isinstance(error, commands.BadArgument):
        with contextlib.suppress(discord.Forbidden):
            await ctx.send(
                f"Unknown channel or invalid "
                f"{arguments} (must be between 0 and 100)."
            )
    else:
        print(f"Ignoring exception in command {ctx.command}:", file=sys.stderr)
        traceback.print_exception(
            type(error),
            error,
            error.__traceback__,
            file=sys.stderr
        )


# ########################
# ### The Bot Instance ###
# ########################

bot = ShirtBot(
    command_prefix=PREFIX,
    help_command=None,
    allowed_mentions=discord.AllowedMentions.none()
)
