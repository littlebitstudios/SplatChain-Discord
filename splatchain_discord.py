import asyncio
from time import sleep
import discord
from discord import app_commands
from discord.ext import tasks
import csv
import re
import secrets
import os
import requests
import yaml

# Global variables
db_file = "./data/splatwallet.csv"
profiles = []

# Loading database
def reload_db():
    global profiles
    with open(db_file, "r") as profiles_csv:
        profiles = list(csv.DictReader(profiles_csv)).copy()
        for profile in profiles:
            if profile['share'] == "True":
                profile['share'] = True
            else:
                profile['share'] = False
                
    if not profiles:
        print("The database is not loaded. Exiting.")
        exit()
        
# Loading block list from internet if enabled
block_list={}
def load_block_list():
    global block_list
    if os.getenv('LBS_BLOCK_LIST') == "true":
        print("Loading block list.")
        listreq = requests.get("https://littlebitstudios.com/splatchain-block-list.yaml")
        block_list = yaml.safe_load(listreq.text)

load_block_list()
    
def user_block_check(user: discord.User):
    global block_list
    if os.getenv('LBS_BLOCK_LIST') == "true":
        if user.name in block_list['blocked_usernames']:
            return True
        if user.id in block_list['blocked_user_ids']:
            return True
    return False

reload_db()

# Detecting duplicates
def detect_duplicates(profiles):
    seen_addresses = set()
    seen_usernames = set()
    for profile in profiles:
        if profile['address'] in seen_addresses:
            print(f"Duplicate address found: {profile['address']}. Removing duplicate.")
            profiles.remove(profile)
        else:
            seen_addresses.add(profile['address'])
        
        if profile['username'] in seen_usernames and profile['username']:
            print(f"Duplicate username found: {profile['username']}. Removing duplicate.")
            profiles.remove(profile)
        else:
            seen_usernames.add(profile['username'])
            
def is_duplicate(profile):
    for other_profile in profiles:
        if profile != other_profile and profile['address'] == other_profile['address']:
            return True
        if profile != other_profile and profile['username'] == other_profile['username']:
            return True
    return False

# Validating profiles
print("Validating profiles in database")

def profile_validator(profile):
    detect_duplicates(profiles)
    
    if 'username' in profile and profile['username']:
        if not profile["username"].endswith(".ink") or not re.match(r"^[a-z0-9.]+$", profile["username"]):
            print(f"Address {profile['address']} has an invalid username of {profile['username']}.")
            print("Usernames must end in .ink and contain only lowercase letters, numbers, and periods!")
            profile["username"] = ""
        
    if re.match(r"[0-9a-fA-F]{40}", profile['address']) is None:
        print(f"Address {profile['address']} has an invalid address. Regenerating address.")
        valid_chars = "0123456789abcdefABCDEF"
        profile['address'] = "".join(secrets.choice(valid_chars) for _ in range(40))
        
    if "," in profile['balance']:
        print(f"Address {profile['address']} has commas in the balance, removing the commas")
        profile['balance'] = profile['balance'].replace(",", "")
    
    if "." in profile['balance']:
        print(f"Address {profile['address']} has a decimal in the balance, removing the decimal")
        profile['balance'] = profile['balance'].replace(".", "")
    
    if not profile['balance'].isnumeric():
        print(f"Address {profile['address']} has an invalid balance of {profile['balance']}.")
        print("Balance must be a number!")
        profile['balance'] = "0"
    
    if profile['type'] not in ["Person", "Business"]:
        if profile['type'] == "person":
            print(f"Profile types must start with a capital letter. Changing {profile['address']}'s type to Person.")
            profile['type'] = "Person"
        elif profile['type'] == "business":
            print(f"Profile types must start with a capital letter. Changing {profile['address']}'s type to Business.")
            profile['type'] = "Business"
        else:
            print(f"Profile types can only be a 'Person' or a 'Business'. Setting type to 'Person' by default.")
            profile['type'] = "Person"
            
for profile in profiles:
    profile_validator(profile)

# Database functions
def write_changes():
    for profile in profiles:
        profile_validator(profile)
    
    with open(db_file, "w", newline='') as profiles_csv:
        writer = csv.DictWriter(profiles_csv, fieldnames=profiles[0].keys())
        writer.writeheader()
        writer.writerows(profiles)

# Discord bot setup
intents = discord.Intents.default()
intents.members = True # Privileged Discord Intent, may require verification if this bot goes public
intents.dm_messages = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

@bot.event
async def on_ready():
    await tree.sync()
    periodic_reload_db.start()
    print("Ready")

@tree.command(name="about", description="Print about information for the SplatChain bot.")
async def about(ctx: discord.Interaction):
    if user_block_check(ctx.user):
        embed=discord.Embed(
            title="BANNED",
            description="You violated the SplatChain Bot Terms and are banned from using the bot.",
            color=discord.colour.Color.red()
        )
        embed.set_footer(text="If you wish to appeal, DM littlebit670.")
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed=discord.Embed(
        title="About SplatChain",
        description="SplatChain is a fictional cryptocurrency system created for Splatoon roleplays.",
        color=discord.colour.Color.blue()
    )
    embed.add_field(name="SPLC's Equivalence", value="A SPLC is equal to 1 cent (US), 100 SPLC is equal to $1.00.\nSPLC is completely fictional and has no real-world value.", inline=False)
    embed.add_field(name="Commands", value="To see all commands, click the Apps icon (it looks like random shapes) and select SplatChain.\nAlternatively, type `/` in the chat and look for the green and pink icon with the dollar sign.", inline=False)
    embed.add_field(name="Enable DMs", value="If you're joining the roleplays, make sure to add me to your account so I can send you DMs. To learn how to do this, run the /testdm command.", inline=False)
    await ctx.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="info", description="List information about a wallet.")    
@app_commands.describe(wallet="The address or username of the wallet to look up.", show="Display this message in the channel (usually this message is private).")
async def list_info(ctx: discord.Interaction, wallet: str, show: bool=False):
    if user_block_check(ctx.user):
        embed=discord.Embed(
            title="BANNED",
            description="You violated the SplatChain Bot Terms and are banned from using the bot.",
            color=discord.colour.Color.red()
        )
        embed.set_footer(text="If you wish to appeal, DM littlebit670.")
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    
    profile = next((profile for profile in profiles if profile["address"] == wallet or profile["username"] == wallet), None)
    
    if profile:
        embed=discord.Embed(
            title=f"Profile Information",
            color=discord.colour.Color.green()
        )
        embed.add_field(name="Address", value=profile["address"], inline=False)
        embed.add_field(name="Nickname", value=profile["nickname"], inline=False)
        embed.add_field(name="Username", value=profile["username"], inline=False)
        embed.add_field(name="Type", value=profile["type"], inline=False)
        embed.add_field(name="Owner", value=profile["owner"], inline=False)
        embed.add_field(name="Balance", value=f"{int(profile['balance']):,} SPLC", inline=False)
        
        if not show:
            embed.set_footer(text="To show this wallet to server members, rerun this command with 'show' set to true.")
        
        await ctx.response.send_message(embed=embed, ephemeral=(not show))
    else:
        await ctx.response.send_message("Could not find a wallet with that address or username.", ephemeral=True)
        
@tree.command(name="new", description="Create a new wallet.")
@app_commands.describe(nickname="The nickname for the new wallet.", username="The username for the new wallet. No spaces or special characters and must end in .ink.", startingbalance="The amount of SPLC that you want this wallet to start with.", type="The type of the wallet, either 'Person' or 'Business'.", share="Allow others to perform destructive actions on this wallet without the bot DMing you.")
@app_commands.choices(type=[
    app_commands.Choice(name="Person", value="Person"),
    app_commands.Choice(name="Business", value="Business")
])
async def new_wallet(ctx: discord.Interaction, nickname: str, username: str, type:str="Person", startingbalance:int=0, share: bool=False):
    if user_block_check(ctx.user):
        embed=discord.Embed(
            title="BANNED",
            description="You violated the SplatChain Bot Terms and are banned from using the bot.",
            color=discord.colour.Color.red()
        )
        embed.set_footer(text="If you wish to appeal, DM littlebit670.")
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return

    new_address = "".join(secrets.choice("0123456789abcdefABCDEF") for _ in range(40))
    
    if not username.endswith(".ink") or not re.match(r"^[a-z0-9.]+$", username):
        embed=discord.Embed(
            title="Invalid Input",
            description="Usernames must end in .ink and contain only lowercase letters, numbers, and periods.",
            color=discord.colour.Color.red()
        )
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    
    new_profile = {
        "address": new_address,
        "nickname": nickname,
        "username": username,
        "type": type,
        "owner": f"discord/{ctx.user.name}",
        "balance": str(startingbalance),
        "share": share
    }
            
    if is_duplicate(new_profile):
        embed=discord.Embed(
            title="Duplicate Username",
            description="A wallet with that username already exists. Try a different username.",
            color=discord.colour.Color.red()
        )
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
            
    profiles.append(new_profile)
    write_changes()
    
    embed=discord.Embed(
        title="New Wallet Created",
        color=discord.colour.Color.green()
    )
    embed.add_field(name="Address", value=new_profile["address"], inline=False)
    embed.add_field(name="Nickname", value=new_profile["nickname"], inline=False)
    embed.add_field(name="Username", value=new_profile["username"], inline=False)
    embed.add_field(name="Type", value=new_profile["type"], inline=False)
    embed.add_field(name="Owner", value=new_profile["owner"], inline=False)
    embed.add_field(name="Balance", value=f"{int(new_profile['balance']):,} SPLC", inline=False)
    embed.add_field(name="Sharing Enabled", value=str(new_profile["share"]), inline=False)
    embed.set_footer(text="Use the /about command to learn more about the bot.\nIt is recommended to run /testdm to make sure that I can send you DMs.")
    await ctx.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="delete", description="Delete a wallet.")
@app_commands.describe(wallet="The address or username of the wallet to delete.", force="Allow deleting a wallet that you do not own. (this will notify the wallet's owner!)")
async def delete_wallet(ctx: discord.Interaction, wallet: str, force: bool=False):
    if user_block_check(ctx.user):
        embed=discord.Embed(
            title="BANNED",
            description="You violated the SplatChain Bot Terms and are banned from using the bot.",
            color=discord.colour.Color.red()
        )
        embed.set_footer(text="If you wish to appeal, DM littlebit670.")
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    
    to_remove = wallet
    profile = next((profile for profile in profiles if profile["address"] == to_remove or profile["username"] == to_remove), None)
    if profile:
        if profile["owner"] != f"discord/{ctx.user.name}" and not force:
            embed=discord.Embed(
                title="Did you mean to do that?",
                description="**You just tried to delete a wallet that you don't own.**\nDouble-check what you entered.\n\n*If you really meant that, try again with 'force' set to true.*",
                color=discord.colour.Color.red()
            )
            
            if profile['share']:
                embed.set_footer(text="Performing destructive actions on a wallet you don't own will notify its owner!\nThis wallet has sharing enabled, but that does NOT mean you can delete it.")
            else:
                embed.set_footer(text="Performing destructive actions on a wallet you don't own will notify its owner!")
            
            await ctx.response.send_message(embed=embed, ephemeral=True)
            return
    
        if profile['owner'] != f"discord/{ctx.user.name}" and force:
            owner_name = profile['owner'].split("/")[1]
            owner = discord.utils.get(bot.get_all_members(), name=owner_name)
            if owner:
                embed=discord.Embed(
                    title="Potentially Unauthorized Action",
                    description=f"{ctx.user.mention} deleted {profile['username']}.",
                    color=discord.colour.Color.red()
                )
                try:
                    await owner.send(embed=embed)
                except discord.Forbidden:
                    print(f"Could not send DM to {owner_name}.")
        
        profiles.remove(profile)
        write_changes()
        await ctx.response.send_message("Wallet deleted.", ephemeral=True)
    else:
        embed = discord.Embed(
            title="Wallet Not Found",
            description="That address or username does not exist.",
            color=discord.colour.Color.red()
        )
        await ctx.response.send_message(embed=embed, ephemeral=True)
        
@tree.command(name="transfer", description="Transfer SPLC between wallets.")
@app_commands.describe(fromwallet="The address or username of the sender.", towallet="The address or username of the receiver.", amount="The amount of SPLC to transfer.", show="Show the transfer message, even if you own both wallets.", force="Allow transferring from a wallet that you do not own. (this will notify the wallet's owner!)")
async def transfer(ctx: discord.Interaction, fromwallet: str, towallet: str, amount: int, force: bool=False, show: bool=False):
    if user_block_check(ctx.user):
        embed=discord.Embed(
            title="BANNED",
            description="You violated the SplatChain Bot Terms and are banned from using the bot.",
            color=discord.colour.Color.red()
        )
        embed.set_footer(text="If you wish to appeal, DM littlebit670.")
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    
    from_profile = next((profile for profile in profiles if profile["address"] == fromwallet or profile["username"] == fromwallet), None)
    to_profile = next((profile for profile in profiles if profile["address"] == towallet or profile["username"] == towallet), None)

    if not from_profile or not to_profile:
        embed = discord.Embed(
            title="Wallet Not Found",
            description="An address or username you gave does not exist.",
            color=discord.colour.Color.red()
        )
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    
    if from_profile["owner"] != f"discord/{ctx.user.name}" and not force:
        embed=discord.Embed(
            title="Did you mean to do that?",
            description="**You just tried to transfer from a wallet that you don't own.**\nDouble-check what you entered.\n\n*If you really meant that, try again with 'force' set to true.*",
            color=discord.colour.Color.red()
        )
        
        if from_profile['share']:
            embed.set_footer(text="This wallet has sharing enabled. Its owner will not be notified if you force this action.")
        else:
            embed.set_footer(text="Performing destructive actions on a wallet you don't own will notify its owner!")
        
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    
    if from_profile['owner'] != f"discord/{ctx.user.name}" and force and not from_profile['share']:
            owner_name = profile['owner'].split("/")[1]
            owner = discord.utils.get(bot.get_all_members(), name=owner_name)
            if owner:
                embed=discord.Embed(
                    title="Potentially Unauthorized Action",
                    description=f"{ctx.user.mention} transferred {amount} SPLC from {from_profile['username']} to {to_profile['username']}.",
                    color=discord.colour.Color.red()
                )
                try:
                    await owner.send(embed=embed)
                except discord.Forbidden:
                    print(f"Could not send DM to {owner_name}.")
    
    if int(from_profile["balance"]) < amount:
        embed=discord.Embed(
            title="Insufficient Balance",
            description="The sender does not have enough SPLC to transfer that amount.",
            color=discord.colour.Color.red()
        )
        embed.add_field(name="Sender Balance", value=f"{int(from_profile['balance']):,} SPLC", inline=False)
        embed.add_field(name="Amount Requested", value=f"{amount:,} SPLC", inline=False)
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return

    from_profile["balance"] = str(int(from_profile["balance"]) - amount)
    to_profile["balance"] = str(int(to_profile["balance"]) + amount)
    write_changes()
    
    if from_profile['owner'] == f"discord/{ctx.user.name}" and to_profile['owner'] == f"discord/{ctx.user.name}" and not show:
        # Hide the message from others if both wallets are owned by the same user
        await ctx.response.send_message(f"{amount:,} SPLC transferred from {from_profile['username']} to {to_profile['username']}.", ephemeral=True)
    else:
        await ctx.response.send_message(f"{from_profile['username']} sent {amount:,} SPLC to {to_profile['username']}.")
    
@tree.command(name="edit", description="Edit a wallet's profile or balance.")
@app_commands.describe(wallet="The address or username of the wallet to edit.", nickname="The new nickname for the wallet.", username="The new username for the wallet.", type="The new type for the wallet.", balance="The new balance for the wallet.", share="Allow others to perform destructive actions on this wallet without the bot DMing you.", force="Allow editing a wallet that you do not own. (this will notify the wallet's owner!)", claim="Take ownership of the wallet.")
@app_commands.choices(type=[
    app_commands.Choice(name="Person", value="Person"),
    app_commands.Choice(name="Business", value="Business")
])
async def edit_profile(ctx: discord.Interaction, wallet: str, nickname: str="", username: str="", type: str="", balance: int=0, share: bool=False, force: bool=False, claim: bool=False):
    if user_block_check(ctx.user):
        embed=discord.Embed(
            title="BANNED",
            description="You violated the SplatChain Bot Terms and are banned from using the bot.",
            color=discord.colour.Color.red()
        )
        embed.set_footer(text="If you wish to appeal, DM littlebit670.")
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    
    input_address = wallet
    profile = next((profile for profile in profiles if profile["address"] == input_address or profile["username"] == input_address), None)
    old_profile = profile.copy()
    
    if profile["owner"] != f"discord/{ctx.user.name}" and not force:
        embed=discord.Embed(
            title="Did you mean to do that?",
            description="**You just tried to edit a wallet that you don't own.**\nDouble-check what you entered.\n\n*If you really meant that, try again with 'force' set to true.*",
            color=discord.colour.Color.red()
        )
        
        if profile['share']:
            embed.set_footer(text="Performing destructive actions on a wallet you don't own will notify its owner!\nThis wallet has sharing enabled, but that does NOT mean you can edit it.")
        else:
            embed.set_footer(text="Performing destructive actions on a wallet you don't own will notify its owner!")
        
        embed.set_footer(text="Performing destructive actions on a wallet you don't own will notify its owner!")
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    
    if profile['owner'] != f"discord/{ctx.user.name}" and force:
            owner_name = profile['owner'].split("/")[1]
            owner = discord.utils.get(bot.get_all_members(), name=owner_name)
            if owner:
                embed=discord.Embed(
                    title="Potentially Unauthorized Action",
                    description=f"{ctx.user.mention} edited {profile['username']}.",
                    color=discord.colour.Color.red()
                )
                try:
                    await owner.send(embed=embed)
                except discord.Forbidden:
                    print(f"Could not send DM to {owner_name}.")
    
    if profile:
        if nickname:
            profile["nickname"] = nickname
            
        if username:
            if not username.endswith(".ink") or not re.match(r"^[a-z0-9.]+$", username):
                await ctx.response.send_message("Invalid username. Usernames must end in .ink and contain only lowercase letters, numbers, and periods.", ephemeral=True)
                return
            profile["username"] = username
            
        if type:
            profile["type"] = type
        
        if balance != 0:
            profile["balance"] = str(balance)
            
        if claim:
            profile["owner"] = f"discord/{ctx.user.name}"
            
        profile['share'] = share
        
        if is_duplicate(profile):
            profiles[profiles.index(profile)] = old_profile.copy()
            embed=discord.Embed(
                title="Duplicate Username",
                description="A wallet with that username already exists. Try a different username.",
                color=discord.colour.Color.red()
            )
            await ctx.response.send_message(embed=embed, ephemeral=True)
            return
        
        write_changes()
        
        embed=discord.Embed(
            title="Profile Updated",
            color=discord.colour.Color.green()
        )
        
        if nickname:
            embed.add_field(name="New Nickname", value=f"{nickname} (was {old_profile['nickname']})", inline=False)
        if username:
            embed.add_field(name="New Username", value=f"{username} (was {old_profile['username']})", inline=False)
        if type:
            embed.add_field(name="New Type", value=f"{type} (was {old_profile['type']})", inline=False)
        if balance:
            embed.add_field(name="New Balance", value=f"{balance:,} SPLC (was {int(old_profile['balance']):,} SPLC)", inline=False)
        if claim:
            embed.add_field(name="New Owner", value=f"discord/{ctx.user.name} (was {old_profile['owner']})", inline=False)
        if share:
            if old_profile['share']:
                embed.add_field(name="New Sharing Enabled State", value=f"{share} (was {old_profile['share']})", inline=False)
            else:
                embed.add_field(name="New Sharing Enabled State", value=f"{share} (was {old_profile['share']})\nSharing Enabled means that others can transfer from or edit this wallet without you being notified.", inline=False)
        await ctx.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(
            title="Wallet Not Found",
            description="An address or username you gave does not exist.",
            color=discord.colour.Color.red()
        )
        await ctx.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="inject", description="Inject SPLC into a wallet.")
@app_commands.describe(wallet="The address or username of the wallet to inject into.", amount="The amount of SPLC to inject.", force="Allow injecting into a wallet that you do not own.")
async def inject_splc(ctx: discord.Interaction, wallet: str, amount: int, force: bool=False):
    if user_block_check(ctx.user):
        embed=discord.Embed(
            title="BANNED",
            description="You violated the SplatChain Bot Terms and are banned from using the bot.",
            color=discord.colour.Color.red()
        )
        embed.set_footer(text="If you wish to appeal, DM littlebit670.")
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    
    if int(amount) < 0:
        await ctx.response.send_message("Amount must be positive.", ephemeral=True)
        return
        
    if int(amount) == 0:
        await ctx.response.send_message("Amount must be nonzero.", ephemeral=True)
        return
    
    profile = next((profile for profile in profiles if profile["address"] == wallet or profile["username"] == wallet), None)
    if profile:
        if profile["owner"] != f"discord/{ctx.user.name}" and not force:
            embed=discord.Embed(
                title="Did you mean to do that?",
                description="**You just tried to inject SPLC a wallet that you don't own.**\nDouble-check what you entered.\n\n*If you really meant that, try again with 'force' set to true.*",
                color=discord.colour.Color.red()
            )
            embed.set_footer(text="Injecting SPLC is not destructive, so forcing this will not notify the wallet's owner.")
            await ctx.response.send_message(embed=embed, ephemeral=True)
            return
        
        
        profile["balance"] = str(int(profile["balance"]) + int(amount))
        write_changes()
        await ctx.response.send_message(f"{amount:,} SPLC injected into {profile['username']}.", ephemeral=True)
    else:
        embed = discord.Embed(
            title="Wallet Not Found",
            description="An address or username you gave does not exist.",
            color=discord.colour.Color.red()
        )
        await ctx.response.send_message(embed=embed, ephemeral=True)
        
@tree.command(name="burn", description="Burn SPLC from a wallet.")
@app_commands.describe(wallet="The address or username of the wallet to burn from.", amount="The amount of SPLC to burn.", force="Allow burning from a wallet that you do not own. (this will notify the wallet's owner!)")
async def burn_splc(ctx: discord.Interaction, wallet: str, amount: int, force: bool=False):
    if user_block_check(ctx.user):
        embed=discord.Embed(
            title="BANNED",
            description="You violated the SplatChain Bot Terms and are banned from using the bot.",
            color=discord.colour.Color.red()
        )
        embed.set_footer(text="If you wish to appeal, DM littlebit670.")
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    
    if int(amount) < 0:
        await ctx.response.send_message("Amount must be positive.", ephemeral=True)
        return
        
    if int(amount) == 0:
        await ctx.response.send_message("Amount must be nonzero.", ephemeral=True)
        return
    
    profile = next((profile for profile in profiles if profile["address"] == wallet or profile["username"] == wallet), None)
    
    if profile:
        if profile["owner"] != f"discord/{ctx.user.name}" and not force:
            embed=discord.Embed(
                title="Did you mean to do that?",
                description="**You just tried to burn SPLC from a wallet that you don't own.**\nDouble-check what you entered.\n\n*If you really meant that, try again with 'force' set to true.*",
                color=discord.colour.Color.red()
            )
            
            if profile['share']:
                embed.set_footer(text="This wallet has sharing enabled. Its owner will not be notified if you force this action.")
            else:
                embed.set_footer(text="Performing destructive actions on a wallet you don't own will notify its owner!")
                
            await ctx.response.send_message(embed=embed, ephemeral=True)
            return
    
        if profile['owner'] != f"discord/{ctx.user.name}" and force:
            owner_name = profile['owner'].split("/")[1]
            owner = discord.utils.get(bot.get_all_members(), name=owner_name)
            if owner:
                embed=discord.Embed(
                    title="Potentially Unauthorized Action",
                    description=f"{ctx.user.mention} burned {amount} SPLC from {profile['username']}.",
                    color=discord.colour.Color.red()
                )
                try:
                    await owner.send(embed=embed)
                except discord.Forbidden:
                    print(f"Could not send DM to {owner_name}.")
        
        if int(profile["balance"]) >= amount:
            profile["balance"] = str(int(profile["balance"]) - amount)
            write_changes()
            await ctx.response.send_message(f"{amount:,} SPLC burned from {profile['username']}.", ephemeral=True)
        else:
            embed = discord.Embed(
                title="Insufficient Balance",
                description="The wallet does not have enough SPLC to burn that amount.",
                color=discord.colour.Color.red()
            )
            embed.add_field(name="Current Balance", value=f"{int(profile['balance']):,} SPLC", inline=False)
            embed.add_field(name="Amount Requested", value=f"{amount:,} SPLC", inline=False)
            await ctx.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(
            title="Wallet Not Found",
            description="An address or username you gave does not exist.",
            color=discord.colour.Color.red()
        )
        await ctx.response.send_message(embed=embed, ephemeral=True)
        
@tree.command(name="mywallets", description="List all wallets you own.")
@app_commands.describe(show="Display this message in the channel (usually this message is private).")
async def my_wallets(ctx: discord.Interaction, show: bool=False):
    if user_block_check(ctx.user):
        embed=discord.Embed(
            title="BANNED",
            description="You violated the SplatChain Bot Terms and are banned from using the bot.",
            color=discord.colour.Color.red()
        )
        embed.set_footer(text="If you wish to appeal, DM littlebit670.")
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    
    owned_by_user = []
    for profile in profiles:
        if profile["owner"] == f"discord/{ctx.user.name}":
            owned_by_user.append(profile)
    
    if len(owned_by_user) == 0:
        embed = discord.Embed(
            title="No Wallets Owned",
            description="It seems that you don't own any wallets.",
            color=discord.colour.Color.red()
        )
        embed.add_field(name="New to SplatChain?", value="Use the /new command to create a new wallet.")
        embed.add_field(name="Thought you owned a wallet?", value="Wallet ownership is based on your Discord username. If you changed your username, use the /edit command on your wallet with 'force' and 'claim' set to true.")
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    else:
        embed=discord.Embed(
            title=("Your Wallets" if not show else f"{ctx.user.name}'s Wallets"),
            color=discord.colour.Color.green()
        )
        
        if show:
            embed.set_footer(text="To see details for a wallet, use the /info command.")
        else:
            embed.set_footer(text="To see details for a wallet, use the /info command.\nRerun this command with 'show' set to true to display this message in the channel.")
        
        for profile in owned_by_user:
            if profile['share']:
                embed.add_field(name=f"{profile['nickname']} ({profile['username']})", value=f"Holds {int(profile['balance']):,} SPLC | **Sharing Enabled**", inline=False)
            else:
                embed.add_field(name=f"{profile['nickname']} ({profile['username']})", value=f"Holds {int(profile['balance']):,} SPLC", inline=False)
            
        await ctx.response.send_message(embed=embed, ephemeral=(not show))

@tree.command(name="userwallets", description="List all wallets owned by a user.")
@app_commands.describe(user="The user to list wallets for.", show="Display this message in the channel (usually this message is private).")
async def user_wallets(ctx: discord.Interaction, user: discord.User, show: bool=False):
    if user_block_check(ctx.user):
        embed=discord.Embed(
            title="BANNED",
            description="You violated the SplatChain Bot Terms and are banned from using the bot.",
            color=discord.colour.Color.red()
        )
        embed.set_footer(text="If you wish to appeal, DM littlebit670.")
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    
    owned_by_user = []
    for profile in profiles:
        if profile["owner"] == f"discord/{user.name}":
            owned_by_user.append(profile)
    
    if len(owned_by_user) == 0:
        await ctx.response.send_message("That user does not own any wallets.", ephemeral=True)
        return
    else:
        embed=discord.Embed(
            title=f"{user.name}'s Wallets",
            color=discord.colour.Color.green()
        )
        embed.set_footer(text="To see details for a wallet, use the /info command.\nWARNING: Performing any destructive action on someone else's wallet will notify them!")
        for profile in owned_by_user:
            if profile['share']:
                embed.add_field(name=f"{profile['nickname']} ({profile['username']})", value=f"Holds {int(profile['balance']):,} SPLC | **Sharing Enabled**", inline=False)
            else:
                embed.add_field(name=f"{profile['nickname']} ({profile['username']})", value=f"Holds {int(profile['balance']):,} SPLC", inline=False)
        await ctx.response.send_message(embed=embed, ephemeral=(not show))
        
@tree.command(name="testdm", description="Send a test DM to yourself.")
async def test_dm(ctx: discord.Interaction):
    if user_block_check(ctx.user):
        embed=discord.Embed(
            title="BANNED",
            description="You violated the SplatChain Bot Terms and are banned from using the bot.",
            color=discord.colour.Color.red()
        )
        embed.set_footer(text="If you wish to appeal, DM littlebit670.")
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    
    try:
        await ctx.user.send("This is a test DM from the SplatChain bot.")
        await ctx.response.send_message("Test DM sent! Check your DMs.", ephemeral=True)
    except discord.Forbidden:
        embed=discord.Embed(
            title="DM Failed",
            description="I could not send you a DM. Here are some things to try.",
            color=discord.colour.Color.red()
        )
        embed.add_field(name="Privacy Settings", value="Make sure that you have DMs enabled for server members.", inline=False)
        embed.add_field(name="Add App to Account", value="Add the SplatChain app to your account. Click [this link](https://discord.com/oauth2/authorize?client_id=1288934248077594797) and select 'Try it Now' in the popup box.")
        embed.add_field(name="Owner/Admin: Re-Invite the Bot", value="If you're an owner or admin, re-invite the bot to the server.\nMake sure you see 'Add a bot to a server' on the page with the Authorize button.", inline=False)
        await ctx.response.send_message(embed=embed, ephemeral=True)
        
@tasks.loop(minutes=5)
async def periodic_reload_db():
    reload_db()
    print("Database reloaded.")
    
@tasks.loop(minutes=5)
async def server_block_check():
    already_pinged_owners = []
    
    if os.getenv('LBS_BLOCK_LIST') == "true" and os.getenv('LBS_BLOCK_SERVERS') == "true":
        for guild in bot.guilds:
            if guild.owner.name in block_list['blocked_usernames'] or guild.owner.id in block_list['blocked_user_ids']:
                if not guild.owner.id in already_pinged_owners:
                    print(f"Owner of {guild.name} is on the block list. Kicking the bot.")
                    embed=discord.Embed(
                    title="This bot has left all of your servers.",
                    description=f"You have been banned from the SplatChain Bot due to a violation of its TOS.\nThis bot has left any servers you own.",
                    color=discord.colour.Color.red()
                    )
                    embed.set_footer(text="If you wish to appeal, DM littlebit670.")
                    await guild.owner.send(embed=embed)
                    already_pinged_owners.append(guild.owner.id)
                    await guild.leave()
            elif guild.id in block_list['blocked_servers']:
                print(f"{guild.name} is on the block list. Kicking the bot.")
                embed=discord.Embed(
                    title=f"This bot has left {guild.name}.",
                    description="Your server has been deemed unacceptable according to the SplatChain Bot Terms.\nThis bot has left your server.",
                    color=discord.colour.Color.red()
                )
                embed.set_footer(text="If you wish to appeal, DM littlebit670.")
                await guild.owner.send(embed=embed)
                await guild.leave()

bot.run(os.getenv('BOT_TOKEN'))