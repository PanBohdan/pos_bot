import bson
import pymongo.database

import discord.ext.commands
from discord.ext import commands
from discord.app_commands import Choice
from typing import List
from discord import app_commands
from misc import chunker
from pymongo import MongoClient
import os
from db_clases import User, Location, Event
from misc import set_locale_autocomplete, get_location_autocomplete, procces_event


m_client = MongoClient(os.environ.get('DB'))
db = m_client['pos_db']
local = db['localized_text']
users = db['users']
servers = db['servers']
languages = db['languages']
events = db['events']


def get_localized_answer(request, locale):
    localized = local.find_one({'request': request})
    if localized:
        return localized['local'].get(locale, localized['local']['default'])


class GM(commands.GroupCog, name="gm"):
    def __init__(self, client):
        self.client = client
        super().__init__()

    @app_commands.command(description='set_image_location_description')
    async def set_image_to_location(self, i: discord.Interaction, role: discord.Role, image: discord.Attachment):

        user = User(i.user.id, i.guild.id)
        loc = Location(role.id, i.guild_id)
        loc.update_image(image.url)
        await i.response.send_message(content=get_localized_answer('set_image_location', user.get_localization()))

    @app_commands.command(description='set_location_desc_description')
    @app_commands.autocomplete(localization=set_locale_autocomplete)
    async def set_location_description(self, i: discord.Interaction, role: discord.Role, description: str, localization: str='default'):
        user = User(i.user.id, i.guild.id)
        loc = Location(role.id, i.guild_id)
        if localization == 'default' or languages.find_one({'language': localization}):
            loc.update_description(description, localization)
            await i.response.send_message(get_localized_answer('set_location_description', user.get_localization()))
            return
        await i.response.send_message(get_localized_answer('generic_error', user.get_localization()))

    @app_commands.command(description='delete_location_description')
    async def delete_location(self, i: discord.Interaction, role: discord.Role):
        user = User(i.user.id, i.guild.id)
        loc = Location(role.id, i.guild_id)
        loc.remove_location(role.id, i.guild_id)
        await i.response.send_message(content=get_localized_answer('delete_location', user.get_localization()))

    @app_commands.command(description='connect_locations_description')
    async def connect(self, i: discord.Interaction, location_1: discord.Role, location_2: discord.Role):
        user = User(i.user.id, i.guild_id)
        loc = Location(location_1.id, i.guild_id)
        loc.attach_or_detach(location_2.id, i.guild.id)
        await i.response.send_message(content=get_localized_answer('link_location',
                                                                   user.get_localization()))

    @app_commands.command(description='create_event_description')
    async def create_event(self, i: discord.Interaction, event: str, location: discord.Role = None, weight: float = 1.,
                           locale: str = 'default'):
        user = User(i.user.id, i.guild_id)
        if location:
            ev = Event(i.guild_id, weight, location.id)
        else:
            ev = Event(i.guild_id, weight)

        ev_read = ev.roc_event()
        ev.edit_event(ev_read['_id'], event, locale)
        await i.response.send_message(get_localized_answer('create_event', user.get_localization()))

    @app_commands.command(description='delete_event_description')
    @app_commands.autocomplete(event_id=get_location_autocomplete)
    async def delete_event(self, i: discord.Interaction, event_id: str):
        user = User(i.user.id, i.guild_id)
        ev = Event(i.guild_id)
        try:
            if event := events.find_one({'_id': bson.ObjectId(event_id)}):
                ev.remove_event(event['_id'])
                await i.response.send_message(get_localized_answer('delete_event', user.get_localization()))
                return
        except bson.errors.InvalidId:
            pass
        await i.response.send_message(get_localized_answer('generic_error', user.get_localization()))

    @app_commands.command(description='set_event_location_description')
    @app_commands.autocomplete(event_id=get_location_autocomplete)
    async def set_event_location(self, i: discord.Interaction, event_id: str, role: discord.Role = None):
        user = User(i.user.id, i.guild_id)
        ev = Event(i.guild_id)
        try:
            if event := events.find_one({'_id': bson.ObjectId(event_id)}):
                if role:
                    ev.change_event_location(event['_id'], role.id)
                else:
                    ev.change_event_location(event['_id'], role)

                await i.response.send_message(get_localized_answer('set_event_location', user.get_localization()))
                return
        except bson.errors.InvalidId:
            pass
        await i.response.send_message(get_localized_answer('generic_error', user.get_localization()))

    @app_commands.command(description='set_event_weight_description')
    @app_commands.autocomplete(event_id=get_location_autocomplete)
    async def set_event_weight(self, i: discord.Interaction, event_id: str, weight: float):
        user = User(i.user.id, i.guild_id)
        ev = Event(i.guild_id, weight=weight)
        try:
            if event := events.find_one({'_id': bson.ObjectId(event_id)}):
                ev.change_event_weight(event['_id'])
                await i.response.send_message(get_localized_answer('set_event_weight', user.get_localization()))
                return
        except bson.errors.InvalidId:
            pass
        await i.response.send_message(get_localized_answer('generic_error', user.get_localization()))

    @app_commands.command(description='set_event_description')
    @app_commands.autocomplete(event_id=get_location_autocomplete, localization=set_locale_autocomplete)
    async def set_event(self, i: discord.Interaction, event_id: str, event_str: str, localization: str = 'default'):
        user = User(i.user.id, i.guild_id)
        ev = Event(i.guild_id)
        try:
            if event := events.find_one({'_id': bson.ObjectId(event_id)}):
                if localization == 'default' or languages.find_one({'language': localization}):
                    ev.edit_event(event['_id'], event_str, localization)
                    await i.response.send_message(get_localized_answer('set_event', user.get_localization()))
                    return
        except bson.errors.InvalidId:
            pass
        await i.response.send_message(get_localized_answer('generic_error', user.get_localization()))

    @app_commands.command(description='get_events_description')
    async def get_events(self, i: discord.Interaction):
        eves = [x for x in events.find({'guild_id': i.guild_id})]
        not_chunked_text = ''
        for x in eves:
            if x['location_id']:
                role = i.guild.get_role(x['location_id']).name
            else:
                role = x['location_id']
            not_chunked_text += f"{str(x['_id']), role} w={x['statistical_weight']}: " \
                                f"{x['localized_events']}\n "
        chunks = chunker(not_chunked_text)
        for n, x in enumerate(chunks):
            if n == 0:
                await i.response.send_message(x)
            else:
                await i.followup.send(x)

    @app_commands.command(description='test_event_description')
    async def test_event(self, i: discord.Interaction, event: str, num_of_times: int = 1):
        output_str = ''
        for x in range(0, num_of_times):
            output_str += procces_event(event)
            output_str += '\n'
        chunks = chunker(output_str)
        for n, x in enumerate(chunks):
            if n == 0:
                await i.response.send_message(x)
            else:
                await i.followup.send(x)


async def setup(client):
    await client.add_cog(GM(client))

