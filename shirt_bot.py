import asyncio
import contextlib
import traceback
import typing
import sys
import random

import discord
from discord.ext import commands

from shirt_bot_utils import *


# ##############
# ### Events ###
# ##############

@bot.event
async def on_ready():
    print('Ready')

    await bot.change_presence(
        activity=discord.Activity(
            name="Shirt Bot",
            type=discord.ActivityType.playing
        )
    )


@bot.listen("on_message")
async def shirt_talk_on_message(message):
    """Event listener that handles shirt talk channels."""

    await bot.wait_until_ready()

    ctx = await bot.get_context(message)

    # Cases where shirt talk doesn't need to trigger:
    #  - the message is a command
    #  - the message author is a bot
    #  - channel is not a shirt talk channel
    #  - message is a non-triggering message
    if (
        ctx.valid or
        message.author.bot or
        message.channel.id not in shirt_talk_channels or
        message.content.startswith("# ")
    ):
        return

    perms = ctx.guild.me.permissions_in(message.channel) if ctx.guild else None
    if (message.guild and not perms.read_message_history):
        with contextlib.suppress(discord.Forbidden):
            await message.channel.send(
                "I need the `Read Message History` "
                "permission to collect messages."
            )
        return
    if message.guild and not perms.manage_messages:
        with contextlib.suppress(discord.Forbidden):
            await message.channel.send(
                "I need the `Manage Messages` permission to delete "
                "no-message triggering ('#') "
                "and forced prompt ('$ ') messages."
            )
        return

    # Whether Shirt Bot will reply to the message or not (if it gets deleted).
    reference = None if (
        (
            message.content == "#" or
            message.content.startswith("$ ")
        ) and not message.guild
    ) else message

    if reference is None:
        with contextlib.suppress(discord.Forbidden):
            await message.delete()

    forced_prompt = f" {message.content[1:].lstrip()}" if (
        message.content.startswith("$ ")
    ) else ""

    try:
        await message.channel.trigger_typing()
    except discord.Forbidden:
        return

    async with message.channel.typing():

        collected_messages = await collect_messages(
            message.channel,
            mode=MessageCollectionType.SHIRT_TALK,
            before=message
        )
        # If the message doesn't get deleted (gets replied to),
        # include it in the prompt.
        if reference is not None:
            collected_messages.append(
                f"{message.author.name}: "
                f"{message.content}"
            )
        collected_messages = '\n'.join(collected_messages)
        collected_messages = shirt_bot_to_shirtman(collected_messages)

        prompt = (
            f"{shirt_bot_to_shirtman(collected_messages)}\n"
            f"Shirtman:{forced_prompt}"
        )
        try:
            response_text = await send_prompt(
                prompt,
                100,
                shirt_talk_channels[message.channel.id]/50,
                ["\n"]
            )
        except (IndexError, KeyError):
            # The API didn't return any text.
            return

    with contextlib.suppress(discord.Forbidden):
        await ctx.shirt_send(
            f"{forced_prompt}{response_text}",
            reference=reference
        )


@bot.listen("on_message")
async def shirt_reply_on_message(message):
    """Event listener that handles shirt reply channels."""

    await bot.wait_until_ready()

    ctx = await bot.get_context(message)

    # Cases where shirt reply doesn't need to trigger:
    #  - the message is a command
    #  - the message author is a bot
    #  - messsage doesn't reply to anyone
    #  - message is in a Shirt Talk channel
    #  - message is not in a shirt reply channel
    #  - message doesn't reply to Shirt Bot
    if (
        ctx.valid or
        message.author.bot or
        not message.reference or
        message.channel.id in shirt_talk_channels or
        message.channel.id not in shirt_reply_channels
    ):
        return
    ref_message = message.reference.resolved if message.reference else None
    if ref_message is None or (
        isinstance(ref_message, discord.DeletedReferencedMessage) or
        ref_message.author != bot.user
    ):
        return

    perms = ctx.guild.me.permissions_in(message.channel) if ctx.guild else None
    if message.guild and not perms.read_message_history:
        with contextlib.suppress(discord.Forbidden):
            await message.channel.send(
                "I need the `Read Message History` "
                "permission to collect messages."
            )
            return
    if message.guild and not perms.manage_messages:
        with contextlib.suppress(discord.Forbidden):
            await message.channel.send(
                "I need the `Manage Messages` permission to delete "
                "no-message triggering ('#') and "
                "forced prompt ('$ ') messages."
            )
            return

    # Whether Shirt Bot will reply to the message or not (if it gets deleted).
    reference = None if (
        message.content == "#" or
        message.content.startswith("$ ")
    ) else message
    if reference is None:
        with contextlib.suppress(discord.Forbidden):
            await message.delete()

    forced_prompt = f" {message.content[1:].lstrip()}" if (
        message.content.startswith("$ ")
    ) else ""

    try:
        await message.channel.trigger_typing()
    except discord.Forbidden:
        return

    async with message.channel.typing():

        collected_messages = await collect_messages(
            message.channel,
            mode=MessageCollectionType.SHIRT_REPLY,
            before=message,
        )
        # If the message doesn't get deleted (gets replied to),
        # include it in the prompt.
        if reference is not None:
            collected_messages.append(
                f"{message.author.name}: "
                f"{message.content}"
            )
        collected_messages = '\n'.join(collected_messages)

        prompt = (
            f"{shirt_bot_to_shirtman(collected_messages)}\n"
            f"Shirtman:{forced_prompt}"
        )
        try:
            response_text = await send_prompt(
                prompt,
                100,
                shirt_reply_channels[message.channel.id]/50,
                ["\n"]
            )
        except IndexError:
            # The API didn't return any text.
            return

    with contextlib.suppress(discord.Forbidden):
        await ctx.shirt_send(
            f"{forced_prompt}{response_text}",
            reference=reference
        )


@bot.listen("on_message")
async def shirt_random_on_message(message):
    """Event listener that handles shirt random channels."""

    await bot.wait_until_ready()

    ctx = await bot.get_context(message)

    # Cases where shirt random doesn't need to trigger:
    #  - the message is a command
    #  - the message author is a bot
    #  - message is in a shirt talk channel
    #  - message is not in a shirt random channel
    #  - message replies to Shirt Bot in a shirt reply channel
    #  - random check fails (check done after permission check)
    if (
        ctx.valid or
        ctx.author.bot or
        ctx.channel.id in shirt_talk_channels or
        ctx.channel.id not in shirt_random_channels
    ):
        return
    ref_message = message.reference.resolved if message.reference else None
    if ctx.channel.id in shirt_reply_channels and ref_message is not None and (
        not isinstance(ref_message, discord.DeletedReferencedMessage) and
        ref_message.author == bot.user
    ):
        return

    perms = ctx.guild.me.permissions_in(ctx.channel) if ctx.guild else None
    if ctx.guild and not perms.read_message_history:
        with contextlib.suppress(discord.Forbidden):
            await ctx.send(
                "I need the `Read Message History` "
                "permission to collect messages."
            )
            return

    if random.uniform(0, 100) >= shirt_random_channels[ctx.channel.id][1]:
        return

    try:
        await ctx.channel.trigger_typing()
    except discord.Forbidden:
        return

    async with ctx.channel.typing():

        collected_messages = await collect_messages(
            ctx.channel,
            mode=MessageCollectionType.TRIGGER_OR_SHIRT_RANDOM
        )
        collected_messages = '\n'.join(collected_messages)

        prompt = (
            f"{shirt_bot_to_shirtman(collected_messages)}\n"
            f"Shirtman:"
        )
        try:
            response_text = await send_prompt(
                prompt,
                100,
                shirt_random_channels[message.channel.id][0]/50,
                ["\n"]
            )
        except IndexError:
            # The API didn't return any text.
            return

    with contextlib.suppress(discord.Forbidden):
        await ctx.shirt_send(
            response_text,
            reference=message
        )


# ################
# ### Commands ###
# ################

# ### Basic Commands ###
@bot.command(name="help", ignore_extra=False)
async def bot_help(ctx, category=''):
    """The help command. Help text is stored in help_text.txt."""
    try:
        await ctx.author.send(
            help_categories[category].format(
                prefix=ctx.prefix
            )
        )
    except discord.Forbidden:
        await ctx.send(
            "Please allow Shirt Bot to "
            "DM you so you can recieve the help. "
            "The help text is very large, "
            "and it would be spammy to send it in a server."
        )
    except KeyError:
        await ctx.send(
            f"Invalid help category. Please use "
            f"{ctx.prefix}help to see all categories."
        )


@bot.command(name="reset", ignore_extra=False)
async def reset_cmd(ctx):
    """Only exists to get detected by the message collector."""


@bot.command(name="echo")
async def echo_cmd(ctx, *, text):
    await ctx.shirt_send(text)


# ### API Commands ###
@bot.command(name="trigger")
async def bot_trigger(
    ctx,
    max_size: typing.Optional[int]=80,
    randomness: typing.Optional[float_nan_converter]=45,
    *,
    text: shirt_bot_to_shirtman=""
):
    """Sends messages as a prompt to the OpenAI API to autocomplete."""

    if randomness > 100 or randomness < 0:
        await ctx.send("Randomness has to be between 0 and 100.")
        return
    if max_size not in range(1, TOKEN_LIMIT+1):
        await ctx.send(f"Max size has to be between 1 and {TOKEN_LIMIT}.")
        return

    perms = ctx.guild.me.permissions_in(ctx.channel) if ctx.guild else None
    if ctx.guild and not perms.read_message_history:
        await ctx.channel.send(
            "I need the `Read Message History` "
            "permission to collect messages."
        )
        return

    async with ctx.channel.typing():
        collected_messages = await collect_messages(
            ctx.channel,
            mode=MessageCollectionType.TRIGGER_OR_SHIRT_RANDOM
        )
        collected_messages = '\n'.join(collected_messages)
        collected_messages = shirt_bot_to_shirtman(collected_messages)
        prompt = f"{collected_messages}\nShirtman:{' ' if text else ''}{text}"
        try:
            response_text = await send_prompt(
                prompt,
                max_size,
                randomness/50,
                ["\n"]
            )
        except (IndexError, KeyError):
            # In case we get no text from the API.
            response_text = ""

    await ctx.shirt_send(f"{text}{response_text}", reference=ctx.message)


@bot.command(name="generate")
async def bot_generate(
    ctx,
    max_size: typing.Optional[int]=80,
    randomness: typing.Optional[float_nan_converter]=45,
    *,
    text=""
):
    """Generates text using the OpenAI API."""

    if randomness > 100 or randomness < 0:
        await ctx.send("Randomness has to be between 0 and 100.")
        return
    if max_size not in range(1, TOKEN_LIMIT+1):
        await ctx.send(f"Max size has to be between 1 and {TOKEN_LIMIT}.")
        return

    async with ctx.channel.typing():
        try:
            response_text = await send_prompt(text, max_size, randomness/50)
        except (IndexError, KeyError):
            # In case we get no text from the API.
            response_text = ""

    await ctx.shirt_send(f"{text}{response_text}", reference=ctx.message)


# ### Shirt Talk Commands ###
@bot.group(name="shirttalk", ignore_extra=False, invoke_without_command=True)
async def shirt_talk(ctx):
    """Adding/removing/listing shirt reply channels."""

    if ctx.guild:
        channels = '\n'.join([
            f"{channel.mention} ({channel.id})\n"
            f"  randomness: {shirt_talk_channels[channel.id]}" for
            channel in
            ctx.guild.text_channels if
            channel.id in shirt_talk_channels
        ])
        if channels:
            await ctx.send(f"List of shirt talk channels:\n\n{channels}")
            return
        await ctx.send("This server doesn't have any shirt talk channels.")
        return
    elif ctx.channel.id in shirt_talk_channels:
        await ctx.send(
            f"This DM channel is a shirt talk channel with "
            f"randomness {shirt_talk_channels[ctx.channel.id]}."
        )
        return
    await ctx.send("This DM channel is not a shirt talk channel.")


@permissions_or_dm(manage_channels=True)
@shirt_talk.command(name="set", ignore_extra=False)
async def shirt_talk_set(
    ctx,
    randomness: typing.Optional[float_nan_converter]=45.0,
    channel: discord.TextChannel=None
):
    """Puts channel in the queue for adding to the shirt talk channels."""

    if randomness < 0 or randomness > 100:
        await ctx.send("Randomness needs to be between 0 and 100.")
        return

    channel = channel or ctx.channel

    await shirt_queue.put((
        "SET_SHIRT_TALK",
        channel.id,
        randomness,
        None
    ))

    channelstr = f" for {channel.mention}" if channel != ctx.channel else ""
    await ctx.send(f"Shirt talk randomness{channelstr} set to {randomness}%.")


@permissions_or_dm(manage_channels=True)
@shirt_talk.command(name="unset", ignore_extra=False)
async def shirt_talk_unset(ctx, channel: discord.TextChannel=None):
    """Puts channel in the queue for removal from the shirt talk channels."""

    channel = channel or ctx.channel
    channelstr = channel.mention if channel != ctx.channel else "This channel"

    if channel.id not in shirt_talk_channels:
        await ctx.send(f"{channelstr} is not a shirt talk channel.")
        return

    await shirt_queue.put((
        "UNSET_SHIRT_TALK",
        channel.id,
        None,
        None
    ))

    channelstr = f" for {channel.mention}" if channel != ctx.channel else ""
    await ctx.send(f"Shirt talk turned off{channelstr}.")


@bot.group(name="shirtreply", ignore_extra=False, invoke_without_command=True)
async def shirt_reply(ctx):
    """Adding/removing/listing shirt reply channels."""

    if ctx.guild:
        channels = '\n'.join([
            f"{channel.mention} ({channel.id})\n"
            f"  randomness: {shirt_reply_channels[channel.id]}%" for
            channel in
            ctx.guild.text_channels if
            channel.id in shirt_reply_channels
        ])
        if channels:
            await ctx.send(f"List of shirt reply channels:\n\n{channels}")
            return
        await ctx.send("This server doesn't have any shirt reply channels.")
        return
    elif ctx.channel.id in shirt_reply_channels:
        await ctx.send(
            f"This DM channel is a shirt reply channel with "
            f"randomness {shirt_reply_channels[ctx.channel.id]}%."
        )
        return
    await ctx.send("This DM channel is not a shirt reply channel.")


@permissions_or_dm(manage_channels=True)
@shirt_reply.command(name="set", ignore_extra=False)
async def shirt_reply_set(
    ctx,
    randomness: typing.Optional[float_nan_converter]=45.0,
    channel: discord.TextChannel=None
):
    """Puts channel in the queue for adding to the shirt reply channels."""

    if randomness < 0 or randomness > 100:
        await ctx.send("Randomness needs to be between 0 and 100.")
        return

    channel = channel or ctx.channel

    await shirt_queue.put((
        "SET_SHIRT_REPLY",
        channel.id,
        randomness,
        None
    ))

    channelstr = f" for {channel.mention}" if channel != ctx.channel else ""
    await ctx.send(f"Shirt reply randomness{channelstr} set to {randomness}%.")


@permissions_or_dm(manage_channels=True)
@shirt_reply.command(name="unset", ignore_extra=False)
async def shirt_reply_unset(ctx, channel: discord.TextChannel=None):
    """Puts channel in the queue for removal from the shirt reply channels."""

    channel = channel or ctx.channel
    channelstr = channel.mention if channel != ctx.channel else "This channel"

    if channel.id not in shirt_reply_channels:
        await ctx.send(f"{channelstr} is not a shirt reply channel.")
        return

    await shirt_queue.put((
        "UNSET_SHIRT_REPLY",
        channel.id,
        None,
        None
    ))

    channelstr = f" for {channel.mention}" if channel != ctx.channel else ""
    await ctx.send(f"Shirt reply turned off{channelstr}.")


@bot.group(name="shirtrandom", ignore_extra=False, invoke_without_command=True)
async def shirt_random(ctx):
    """Adding/removing/listing shirt random channels."""

    if ctx.guild:
        channels = '\n'.join([
            f"{channel.mention} ({channel.id})\n"
            f"  randomness: {shirt_random_channels[channel.id][0]}%\n"
            f"  chance: {shirt_random_channels[channel.id][1]}%" for
            channel in
            ctx.guild.text_channels if
            channel.id in shirt_random_channels
        ])
        if channels:
            await ctx.send(f"List of shirt random channels:\n\n{channels}")
            return
        await ctx.send("This server doesn't have any shirt random channels.")
        return
    elif ctx.channel.id in shirt_random_channels:
        await ctx.send(
            f"This DM channel is a shirt random channel with "
            f"randomness {shirt_random_channels[ctx.channel.id][0]}% and "
            f"chance {shirt_random_channels[ctx.channel.id][1]}%."
        )
        return
    await ctx.send("This DM channel is not a shirt random channel.")


@permissions_or_dm(manage_channels=True)
@shirt_random.command(name="set", ignore_extra=False)
async def shirt_random_set(
    ctx,
    randomness: typing.Optional[float_nan_converter]=45.0,
    chance: typing.Optional[float_nan_converter]=5.0,
    channel: discord.TextChannel=None
):
    """Puts channel in the queue for adding to the shirt random channels."""

    if randomness < 0 or randomness > 100:
        await ctx.send("Randomness needs to be between 0 and 100.")
        return
    if chance < 0 or chance > 100:
        await ctx.send("Chance needs to be between 0 and 100.")
        return

    channel = channel or ctx.channel

    await shirt_queue.put((
        "SET_SHIRT_RANDOM",
        channel.id,
        randomness,
        chance
    ))

    channelstr = f" for {channel.mention}" if channel != ctx.channel else ""
    await ctx.send(
        f"Shirt random{channelstr} set to\n"
        f"  randomness: {randomness}%\n"
        f"  chance: {chance}%"
    )


@permissions_or_dm(manage_channels=True)
@shirt_random.command(name="unset", ignore_extra=False)
async def shirt_random_unset(ctx, channel: discord.TextChannel=None):
    """Puts channel in the queue for removal from the shirt random channels."""

    channel = channel or ctx.channel
    channelstr = channel.mention if channel != ctx.channel else "This channel"

    if channel.id not in shirt_random_channels:
        await ctx.send(f"{channelstr} is not a shirt random channel.")
        return

    await shirt_queue.put((
        "UNSET_SHIRT_RANDOM",
        channel.id,
        None,
        None
    ))

    channelstr = f" for {channel.mention}" if channel != ctx.channel else ""
    await ctx.send(f"Shirt random turned off{channelstr}.")


@bot.group(name="links", ignore_extra=False, invoke_without_command=True)
async def links(ctx):
    """Uncensoring links or listing channels with uncensored links."""

    if ctx.guild:
        channels = '\n'.join([
            f"  {channel.mention} ({channel.id})" for
            channel in
            ctx.guild.text_channels if
            channel.id in uncensored_link_channels
        ])
        if channels:
            await ctx.send(f"Channels with uncensored links:\n{channels}")
            return
        await ctx.send(
            "This server doesn't have any "
            "channels with uncensored links."
        )
        return
    elif ctx.channel.id in uncensored_link_channels:
        await ctx.send(f"This DM channel has uncensored links.")
        return
    await ctx.send("This DM channel has censored links.")


@permissions_or_dm(manage_channels=True)
@links.command(name="toggle", ignore_extra=False)
async def links_toggle(ctx, channel: discord.TextChannel=None):
    """Puts channel in the queue for toggling censoring channels."""

    channel = channel or ctx.channel
    channelstr = channel.mention if channel != ctx.channel else "This channel"

    if channel.id in uncensored_link_channels:
        op = "CENSOR_LINKS"
    else:
        op = "UNCENSOR_LINKS"

    await shirt_queue.put((
        op,
        channel.id,
        None,
        None
    ))

    channelstr = f" for {channel.mention}" if channel != ctx.channel else ""
    if op == "CENSOR_LINKS":
        await ctx.send(f"Links censored{channelstr}.")
        return
    await ctx.send(f"Links uncensored{channelstr}.")


# ######################
# ### Error Handlers ###
# ######################

@bot.event
async def on_command_error(ctx, error):
    error = getattr(error, "original", error)
    ignored = (
        commands.CommandNotFound,
        commands.TooManyArguments,
        discord.Forbidden,
        discord.HTTPException
    )
    if hasattr(ctx.command, 'on_error'):
        pass
    elif isinstance(error, ignored):
        pass
    else:
        print(f"Ignoring exception in command {ctx.command}:", file=sys.stderr)
        traceback.print_exception(
            type(error),
            error,
            error.__traceback__,
            file=sys.stderr
        )


@shirt_talk_set.error
async def error__shirt_talk_set(ctx, error):
    await handle_set_error(ctx, error, "randomness")


@shirt_talk_unset.error
async def error__shirt_talk_unset(ctx, error):
    await handle_unset_or_toggle_error(ctx, error)


@shirt_reply_set.error
async def error__shirt_reply_set(ctx, error):
    await handle_set_error(ctx, error, "randomness")


@shirt_reply_unset.error
async def error__shirt_reply_unset(ctx, error):
    await handle_unset_or_toggle_error(ctx, error)


@shirt_random_set.error
async def error__shirt_random_set(ctx, error):
    await handle_set_error(ctx, error, "randomness or chance")


@shirt_random_unset.error
async def error__shirt_reply_unset(ctx, error):
    await handle_unset_or_toggle_error(ctx, error)


@links_toggle.error
async def error__links_toggle(ctx, error):
    await handle_unset_or_toggle_error(ctx, error)


# #######################
# ### Running The Bot ###
# #######################


clean_unused_channels.start()
loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(bot.start(BOT_TOKEN))
except KeyboardInterrupt:
    loop.run_until_complete(bot.logout())
    update_data_files.stop()
    clean_unused_channels.stop()
finally:
    discord.client._cleanup_loop(loop)
