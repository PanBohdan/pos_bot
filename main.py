import discord
from discord.ext.commands import Bot
import os
from pymongo import MongoClient
from discord.app_commands import Translator
from cogs.pos import PoS
from cogs.gm import GM
from cogs.admin import Admin
try:
    from secret import *
except ImportError:
    pass

intent = discord.Intents.all()
m_client = MongoClient(os.environ.get('DB'))
db = m_client['pos_db']
local = db['localized_commands']


# Main settings
TOKEN = os.environ.get('TOKEN')
prefix = '.'

# Cogs setup
cogs_dir = 'cogs'
dict_of_cog_names_and_classes = {'pos': PoS, 'gm': GM, 'admin': Admin}
list_of_full_cog_path = [f"{cogs_dir}.{cog}" for cog in dict_of_cog_names_and_classes.keys()]

# Bot setup
client = Bot(prefix, intents=intent, application_id=int(os.environ.get('APP_ID')))
client.synced = False


class Translation(Translator):
    def __init__(self):
        super().__init__()
        self.command = {}
        for locale in local.find():
            self.command[locale['command']] = locale['local']

    async def translate(self, locale_str, locale, context):
        if localized := self.command.get(str(locale_str), None):
            if localized_fin := localized.get(str(locale), None):
                return localized_fin
            elif localized_fin := localized.get('default', None):
                return localized_fin
        return None


@client.event
async def on_ready():
    print(f'Translation in progress')
    await client.tree.set_translator(Translation())
    for cog in list_of_full_cog_path:
        try:
            await client.load_extension(cog)
        except discord.ext.commands.ExtensionAlreadyLoaded:
            await client.reload_extension(cog)
    if not client.synced:
        await client.tree.sync()
        client.synced = True
    await client.wait_until_ready()

    print(f'Logged in as: {client.user.name}')
    print(f'With ID: {client.user.id}')
    print(f'Loaded cogs: {list(dict_of_cog_names_and_classes.keys())}')


if __name__ == '__main__':
    client.run(TOKEN)
