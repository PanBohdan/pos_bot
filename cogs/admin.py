import discord.ext.commands
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
import os
from db_clases import User, Server
from misc import get_localized_answer
m_client = MongoClient(os.environ.get('DB'))
db = m_client['pos_db']
users = db['users']
servers = db['servers']
languages = db['languages']
events = db['events']


class Admin(commands.GroupCog, name="admin"):
    def __init__(self, client):
        self.client = client
        super().__init__()

    @app_commands.command(description='set_manual_url_description')
    async def set_manual_url(self, i: discord.Interaction, url: str):
        user = User(i.user.id, i.guild.id)
        Server(i.guild.id).set_manual_url(url)
        await i.response.send_message(content=get_localized_answer('set_manual_url', user.get_localization()))


async def setup(client):
    await client.add_cog(Admin(client))

