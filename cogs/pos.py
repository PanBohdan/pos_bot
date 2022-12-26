import discord.ext.commands
from discord.ext import commands
from discord import app_commands
from misc import set_locale_autocomplete, chunker, procces_event
from pymongo import MongoClient
import os
from typing import List
from discord import SelectOption
from discord.ui import Select, View, Button, Modal, TextInput
from db_clases import User, Location, Event
from placeholders import move_url_placeholder
import random

m_client = MongoClient(os.environ.get('DB'))
db = m_client['pos_db']
local = db['localized_text']
users = db['users']
servers = db['servers']
languages = db['languages']
locations = db['locations']
roles = db['roles']
events = db['events']


def update_events_and_weights(event_list, localization, fin_eve_list, weight_list):
    for x in event_list:
        fin_eve_list.append(x['localized_events'].get(localization, x['localized_events']['default']))
        weight_list.append(x['statistical_weight'])


def get_localized_answer(request, locale):
    localized = local.find_one({'request': request})
    if localized:
        return localized['local'].get(locale, localized['local']['default'])


class PoS(commands.GroupCog, name="pos"):
    def __init__(self, client):
        self.client = client
        super().__init__()

    @app_commands.command(description='set_localization_description')
    @app_commands.autocomplete(choices=set_locale_autocomplete)
    async def set_localization(self, i: discord.Interaction, choices: str):
        user = User(i.user.id, i.guild.id)
        if languages.find_one({'language': choices}):
            user.set_localization(choices)
            await i.response.send_message(content=get_localized_answer('set_localization_good_answer',
                                                                       user.get_localization()), ephemeral=True)
        else:
            await i.response.send_message(content=get_localized_answer('set_localization_bad_answer',
                                                                       user.get_localization()), ephemeral=True)

    @app_commands.command(description='move_description')
    async def move(self, i: discord.Interaction):
        async def inter_check(inte):
            return inte.user.id == i.user.id

        user = User(i.user.id, i.guild.id)
        locs = []
        for loc in locations.find():
            if role := i.user.get_role(loc['id']):
                locs.append(role)

        if 25 >= len(locs) >= 1:
            if len(locs) > 1:
                need_selection = True

            else:
                need_selection = False
            selected_location = locs

            async def starting_location_callback(inter: discord.Interaction):
                selected_location[0] = inter.guild.get_role(int(select_starting_location.values[0]))

                new_opts = [SelectOption(label=inter.guild.get_role(x).name, value=x) for x in
                            Location(selected_location[0].id, inter.guild_id).roc_location()['attached_locations']]
                view_location.remove_item(select_location)
                select_location.options = new_opts
                view_location.add_item(select_location)
                embed = discord.Embed(title=get_localized_answer('select_location_to_move', user.get_localization()))
                desc = '. . .'
                if dsc_col := Location(selected_location[0].id, inter.guild_id).roc_location().get('description'):
                    desc = dsc_col.get(user.get_localization(), dsc_col['default'])
                embed.add_field(name=get_localized_answer('now_on_location', user.get_localization()).format(inter.guild.get_role(selected_location[0].id)), value=desc)
                embed.set_image(url=Location(selected_location[0].id, i.guild_id).roc_location().get('url', move_url_placeholder))

                await inter.response.edit_message(embed=embed, view=view_location)

            starting_view = View()
            starting_view.interaction_check = inter_check
            options = [SelectOption(label=x.name, value=str(x.id)) for x in locs]
            select_starting_location = Select(options=options)
            select_starting_location.callback = starting_location_callback
            starting_view.add_item(select_starting_location)

            async def select_location_callback(inter: discord.Interaction):
                await inter.user.add_roles(inter.guild.get_role(int(select_location.values[0])))
                await inter.user.remove_roles(inter.guild.get_role(selected_location[0].id))
                view_location.remove_item(select_location)
                new_opts = [SelectOption(label=inter.guild.get_role(y).name, value=y)
                            for y in Location(int(select_location.values[0]),
                                              inter.guild_id).roc_location()['attached_locations']]
                last_location = inter.guild.get_role(selected_location[0].id)
                selected_location[0] = inter.guild.get_role(int(select_location.values[0]))
                select_location.options = new_opts
                view_location.add_item(select_location)
                embed = discord.Embed(title=get_localized_answer('select_location_to_move', user.get_localization()))
                desc = '. . .'
                if dsc_col := Location(int(select_location.values[0]), inter.guild_id).roc_location().get('description'):
                    desc = dsc_col.get(user.get_localization(), dsc_col['default'])
                embed.add_field(name=get_localized_answer('now_on_location', user.get_localization()).format(inter.guild.get_role(selected_location[0].id)),
                                value=desc)
                embed.set_image(url=Location(int(select_location.values[0]), i.guild_id).roc_location().get('url', move_url_placeholder))

                await inter.response.edit_message(view=view_location, embed=embed)
                await i.followup.send(get_localized_answer('move_location',
                                                           user.get_localization()).format(inter.user.mention,
                                                                                           last_location.name,
                                                                                           inter.guild.get_role(int(
                                                                                               select_location.values[
                                                                                                   0])).name))
                for r in roles.find({'movement_number': True}).sort('chance', -1):
                    if i.user.get_role(r['id']):
                        num = random.randint(1, 100)
                        if r['chance'] >= num:
                            event_list = []
                            weight_list = []
                            localize = user.get_localization()
                            update_events_and_weights(events.find({'location_id': None}), localize, event_list, weight_list)
                            update_events_and_weights(events.find({'location_id': last_location.id}), localize, event_list, weight_list)
                            update_events_and_weights(events.find({'location_id': int(select_location.values[0])}), localize, event_list, weight_list)
                            event = random.choices(event_list, cum_weights=weight_list)[0]
                            await i.followup.send(f'{get_localized_answer("location", user.get_localization())}\n'
                                                  f'{procces_event(event)}')
                        break

            select_location_opts = [SelectOption(label=i.guild.get_role(x).name, value=x)
                                    for x in Location(selected_location[0].id,
                                                      i.guild_id).roc_location()['attached_locations']]
            view_location = View()
            view_location.interaction_check = inter_check
            select_location = Select(options=select_location_opts)
            select_location.callback = select_location_callback
            view_location.add_item(select_location)
            if not need_selection:
                embed = discord.Embed(title=get_localized_answer('select_location_to_move', user.get_localization()))
                desc = '. . .'
                if dsc_col := Location(selected_location[0].id, i.guild_id).roc_location().get('description'):
                    desc = dsc_col.get(user.get_localization(), dsc_col['default'])

                embed.add_field(name=get_localized_answer('now_on_location', user.get_localization()).format(selected_location[0].name),
                                value=desc)
                embed.set_image(url=Location(selected_location[0].id, i.guild_id).roc_location().get('url', move_url_placeholder))
                await i.response.send_message(embed=embed, view=view_location)
            else:
                await i.response.send_message(content=get_localized_answer('select_location', user.get_localization()),
                                              view=starting_view)
        else:
            await i.response.send_message(get_localized_answer('error_location', user.get_localization()))

    @app_commands.command(description='get_locations_description')
    async def get_locations(self, i: discord.Interaction):
        locs = [x for x in locations.find({'guild_id': i.guild_id})]
        not_chunked_text = ''
        for x in locs:
            not_chunked_text += f"{i.guild.get_role(x['id']).name} : " \
                                f"{[i.guild.get_role(y).name for y in x['attached_locations']]}\n"
        chunks = chunker(not_chunked_text)
        for n, x in enumerate(chunks):
            if n == 0:
                await i.response.send_message(x)
            else:
                await i.followup.send(x)


async def setup(client):
    await client.add_cog(PoS(client))

