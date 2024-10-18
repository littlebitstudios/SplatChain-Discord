# SplatChain - a fictional cryptocurrency

[![forthebadge](https://forthebadge.com/images/badges/made-with-python.svg)](https://forthebadge.com)
[![forthebadge](https://forthebadge.com/images/badges/docker-container.svg)](https://forthebadge.com)
[![forthebadge](https://forthebadge.com/images/badges/license-mit.svg)](https://forthebadge.com)

The SplatChain Bot is a Discord bot designed for roleplaying (namely in the Splatoon universe), with a fictional cryptocurrency called SPLC.
It is designed to allow roleplayers to create fake transactions so that there can be an economy in their part of the Splatoon universe.

## Install the Bot
You may install my instance of the bot by clicking [here](https://discord.com/oauth2/authorize?client_id=1288934248077594797).
If you host your own instance you can find the invite link in the Discord Developer Portal.

## Host your own instance
This repository hosts a container image you may use to host your own instance of the bot.

Please keep in mind that wallet data is not shared between instances; each one has its own copy of the splatwallet.csv file.

Requires:
1. a computer with Docker installed, preferably one that remains on 24/7
2. a Discord bot token (creating a bot is free, go to the [Discord Developer Portal](https://discord.com/developers/applications) to create one)

Create a folder to hold the bot's data. Inside the folder, create another folder called `data`.

Copy the `splatwallet-example.csv` file from this repository into `data` and rename it to `splatwallet.csv`.

In the root of the bot's folder, copy the `example-compose.yml` file and rename it to `compose.yml`.

In the `environment:` section of the Compose file, you'll see two variables: `BOT_TOKEN` and `LBS_BLOCK_LIST`. Add the Discord bot token to the `BOT_TOKEN` variable. If you want to apply the LittleBit Studios block list, set `LBS_BLOCK_LIST` to `true`. Keep in mind that Section 1 of the SplatChain Bot Terms applies to your instance if the block list is enabled. You may also opt to fully adopt the SplatChain Bot Terms by setting `LBS_BLOCK_SERVERS` to `true`.

## Rules
The rules of this bot are governed by the SplatChain Bot Terms, found at https://littlebitstudios.com/splatchain-terms.html.

Discord requires that bots also publish a privacy policy. The SplatChain Bot's privacy policy is found at https://littlebitstudios.com/splatchain-privacy.html. To cut it short; the only data the bot handles is Discord usernames/user IDs/server IDs, and any data the user enters manually in interactions with the bot. I do not share data my bot collects with any company.

## Credits
This bot is written using the [discord.py](https://discordpy.readthedocs.io/en/latest/) library.

The badges at the top of this README are made by For The Badge (https://forthebadge.com).

Splatoon is a game owned by Nintendo Co. Ltd. and international subsidiaries. LittleBit Studios is not affiliated with Nintendo, and no game assets are used in this bot.

This bot is open-source software, under the MIT license. See the LICENSE file for the license text.

The SplatChain Bot's icon is an original design by me, and may be used as the profile picture for self-hosted instances of the bot.
