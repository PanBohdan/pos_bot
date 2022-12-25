import discord
from discord.ext.commands import Bot
import os
from pymongo import MongoClient
from discord.app_commands import Translator
try:
    from secret import *
except ImportError:
    pass
intent = discord.Intents.all()
from cogs.pos import PoS
from cogs.gm import GM
m_client = MongoClient(os.environ.get('DB'))
db = m_client['pos_db']
local = db['localized_commands']


# Main settings
TOKEN = os.environ.get('TOKEN')
prefix = '.'

# Cogs setup
cogs_dir = 'cogs'
dict_of_cog_names_and_classes = {'pos': PoS, 'gm': GM}
list_of_full_cog_path = [f"{cogs_dir}.{cog}" for cog in dict_of_cog_names_and_classes.keys()]

# Bot setup
client = Bot(prefix, intents=intent, application_id=int(os.environ.get('APP_ID')))
client.synced = False


class Translation(Translator):
    def __init__(self):
        super().__init__()

    async def translate(self, locale_str, locale, context):
        if localized := local.find_one({'command': str(locale_str)}):
            if localized_fin := localized['local'].get(str(locale), None):
                return localized_fin
            elif localized_fin := localized['local'].get('default', None):
                return localized_fin
        return None


@client.event
async def on_ready():
    # await client.tree.set_translator(Translation())
    for cog in list_of_full_cog_path:
        await client.load_extension(cog)
    if not client.synced:
        await client.tree.sync()
        client.synced = True
    print(f'Logged in as: {client.user.name}')
    print(f'With ID: {client.user.id}')
    print(f'Loaded cogs: {list(dict_of_cog_names_and_classes.keys())}')


if __name__ == '__main__':
    client.run(TOKEN)
