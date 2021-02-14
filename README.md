# SHIRT BOT &middot; [![License: Unlicense](https://img.shields.io/badge/license-Unlicense-blue.svg)](https://unlicense.org/) [![Language: Python 3](https://img.shields.io/badge/language-Python%203-blue.svg)](https://python.org/)  
Shirt Bot is a discord bot which uses GPT-3 to generate text.<br>
Made by Cyclcrclicly#3420 (474183744685604865) on Discord.<br>
[Support Server](https://discord.gg/KXxnPSScdn)
# EXAMPLES
![example1](https://media.discordapp.net/attachments/538700981030879242/810570370829516871/example_1.png)
![example2](https://media.discordapp.net/attachments/538700981030879242/810570389729443900/example_2.png)
![example3](https://media.discordapp.net/attachments/538700981030879242/810570428228698122/example_3.png)
![example4](https://media.discordapp.net/attachments/538700981030879242/810570461942513724/example_4.png)
![example5](https://media.discordapp.net/attachments/538700981030879242/810570479677079562/example_5.png)
![example6](https://media.discordapp.net/attachments/538700981030879242/810570503349075968/example_6.png)
# HELP
## COMMAND HELP
### ARGUMENT EXPLANATION
```
<argument>            required argument
[argument]            optional argument
[argument=default]    optional argument with a default value
The order of optional arguments matters.
```
### COMMAND ARGUMENTS
```
max_size      the maximum size in tokens (word segments)
randomness    how random the output message will be as a percentage
chance        how likely the bot is to trigger as a percentage
text          extra text
channel       the channel which the command will affect
```
### COMMANDS
```
generate [max_size=80] [randomness=45] [text]
  Generates text.
  
trigger [max_size=80] [randomness=45] [text]
  Generates text with the last 15 non-command messages as context.

shirttalk
  In a server    lists shirt talk channels
  In a DM        states if shirt talk is on in the DM channel
shirttalk set [randomness=45] [channel=message channel]
  Sets up a shirt talk channel.
shirttalk unset [channel=message channel]
  Removes a shirt talk channel.

shirtreply
  In a server    lists shirt reply channels
  In a DM        states if shirt reply is on in the DM channel
shirtreply set [randomness=45] [channel=message channel]
  Sets up a shirt reply channel.
shirtreply unset [channel=message channel]
  Removes a shirt reply channel.

shirtrandom
  In a server    lists shirt random channels
  In a DM        states if shirt random is on in the DM channel
shirtrandom set [randomness=45] [chance=5] [channel=message channel]
  Sets up a shirt random channel.
shirtreply unset [channel=message channel]
  Removes a shirt random channel.

reset
  Once the bot encounters this command, it stops collecting further messages as context.

echo <text>
  Repeats text.

links
  In a server    lists all channels with uncensored links
  In a DM        states if DM channel has (un)censored links
links toggle [channel=message channel]
  Toggles censoring links in a channel.
```
## SHIRT TALK HELP
```
Shirt talk is a feature of Shirt Bot which lets it automatically reply to all messages sent in a channel.
By default, it's off for all channels, but you can set it up using the shirttalk set command.
The extras that work in shirt talk channels are '#', '# ', and '$ '.
Shirt talk also works in DMs.
```
## SHIRT REPLY HELP
```
Shirt reply is a feature of Shirt Bot which lets it trigger when you reply to one of the bot's messages.
By default, it's off for all channels, but you can set it up using the shirtreply set command.
The extras which work in shirt reply channels are '#' and '$ '.
Shirt reply also works in DMs.
```
## SHIRT RANDOM HELP
```
Shirt random is a feature of Shirt Bot which lets it trigger randomly (customizable chance) whenever a message is sent in a channel where it's on.
By default, it's off for all channels, but you can set it up using the shirtman set command.
Extras don't work here.
Shirt random also works in DMs.
```
## PRECEDENCE
```
Precedence is a way to organize the bot's features into a hierarchy. If a feature is on/triggered, it prevents some other features from triggering.
The precedence is:

  Commands
    if your message is a command, it prevents everything below from triggering

  Shirt talk
    if your message is in a shirt talk channel, it prevents everything below from triggering
    if none of the above features are on/triggered, shirt talk can trigger

  Shirt reply
    if your message replies to shirt bot in a shirt reply channel, it prevents everything below from triggering
    if none of the above features are on/triggered, shirt reply can trigger

  Shirt random
    if none of the above features are on/triggered, shirt random can trigger
```
## EXTRAS
```
Extras are extra features of Shirt Bot which work in shirt talk and shirt reply. The helps for those list exactly which extras work.
Extras are:

  '#'     if your message only contains '#', Shirt Bot will try to delete the message (unless in a DM) and trigger. This allows you to trigger the bot multiple times without having to type any new messages in between.

  '# '    if your message starts with '# ', Shirt Bot will ignore the message (i.e. won't trigger), but will actually collect the message once an actual trigger occurs. This allows you to type multiple messages before triggering the bot if you wish to do that.

  '$ '    if your message starts with '$ ', it will force Shirt Bot to start its next message with the content of your message. This way, you can force Shirt Bot to say something it otherwise may not have said.
```
# REQUIREMENTS
[python](https://www.python.org/) - at least 3.6<br>
[regex](https://pypi.org/project/regex/)<br>
[aiohttp](https://pypi.org/project/aiohttp/)<br>
[discord.py](https://pypi.org/project/discord.py/) - at least 1.6.0
# INSTRUCTIONS
1. Install all requirements. You can use `pip install -r requirements.txt` or install them manually.
2. Create a `config.json` file from the `config.json.template` file and fill it out with the correct information.
3. Run `shirt_bot.py`.
# CREDIT
All the contents of the encoder folder are from https://github.com/latitudegames/GPT-3-Encoder and are thus licensed with [the MIT License](encoder/LICENSE).<br>
URL matching regex pattern is from: https://stackoverflow.com/a/17773849
