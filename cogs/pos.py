import discord.ext.commands
from discord.ext import commands
from discord import app_commands
from misc import set_locale_autocomplete, chunker, procces_event, get_localized_answer, update_events_and_weights
from pymongo import MongoClient
import os
from typing import List
from views import ManualView, ManualSelect
from discord import SelectOption
from discord.ui import Select, View, Button, Modal, TextInput
from db_clases import User, Location, Event, Server
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
        localize = user.get_localization()
        now_on_location_answer = get_localized_answer('now_on_location', localize)
        select_location_to_move = get_localized_answer('select_location_to_move', localize)
        move_location_answer = get_localized_answer('move_location', localize)
        location_answer = get_localized_answer("location", localize)

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
                embed = discord.Embed(title=select_location_to_move)
                desc = '. . .'
                if dsc_col := Location(selected_location[0].id, inter.guild_id).roc_location().get('description'):
                    desc = dsc_col.get(localize, dsc_col['default'])
                embed.add_field(name=now_on_location_answer.format(inter.guild.get_role(selected_location[0].id)), value=desc)
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
                last_location = inter.guild.get_role(selected_location[0].id)
                desc = '. . .'
                if dsc_col := Location(int(select_location.values[0]), inter.guild_id).roc_location().get('description'):
                    desc = dsc_col.get(localize, dsc_col['default'])
                embed = discord.Embed(title=now_on_location_answer.format(inter.guild.get_role(int(select_location.values[0]))),
                                      description=desc)
                embed.set_image(url=Location(int(select_location.values[0]), i.guild_id).roc_location().get('url', move_url_placeholder))

                await inter.response.edit_message(view=None, embed=embed)
                await i.followup.send(move_location_answer.format(inter.user.mention,
                                                                  last_location.name,
                                                                  inter.guild.get_role(
                                                                      int(select_location.values[0])).name))
                for r in roles.find({'movement_number': True}).sort('chance', -1):
                    if i.user.get_role(r['id']):
                        num = random.randint(1, 100)
                        if r['chance'] >= num:
                            await i.user.add_roles(inter.guild.get_role(roles.find_one({'event_role': True})['id']))

                            event_list = []
                            weight_list = []
                            update_events_and_weights(events.find({'location_id': last_location.id}), localize, event_list, weight_list)
                            update_events_and_weights(events.find({'location_id': int(select_location.values[0])}), localize, event_list, weight_list)
                            update_events_and_weights(events.find({'location_id': None}), localize, event_list, weight_list)
                            event = random.choices(event_list, weights=weight_list)[0]
                            if event[2]:
                                loc_text = f"({i.guild.get_role(event[2]).name})"
                            else:
                                if not events.find({'location_id': last_location.id}):
                                    loc_text = f"({last_location.name})"
                                else:
                                    loc_text = f"({inter.guild.get_role(int(select_location.values[0])).name})"

                            emb = discord.Embed()
                            emb.add_field(name=f'{loc_text} {location_answer}',
                                          value=procces_event(event[0]))
                            if url := event[1]:
                                emb.set_image(url=url)
                            await i.followup.send(content=f'{inter.user.mention}', embed=emb)
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
                embed = discord.Embed(title=select_location_to_move)
                desc = '. . .'
                if dsc_col := Location(selected_location[0].id, i.guild_id).roc_location().get('description'):
                    desc = dsc_col.get(localize, dsc_col['default'])

                embed.add_field(name=now_on_location_answer.format(selected_location[0].name),
                                value=desc)
                embed.set_image(url=Location(selected_location[0].id, i.guild_id).roc_location().get('url', move_url_placeholder))
                await i.response.send_message(embed=embed, view=view_location)
            else:
                await i.response.send_message(content=get_localized_answer('select_location', localize),
                                              view=starting_view)
        else:
            await i.response.send_message(get_localized_answer('error_location', localize))

    @app_commands.command(description='get_locations_description')
    async def get_locations(self, i: discord.Interaction):
        locs = [x for x in locations.find({'guild_id': i.guild_id})]
        not_chunked_text = ''
        for x in locs:
            not_chunked_text += f"```css\n#{i.guild.get_role(x['id']).name}:\n"
            for n, sub_loc in enumerate(x['attached_locations']):
                not_chunked_text += f"- {i.guild.get_role(sub_loc).name}"
                if n != len(x['attached_locations'])-1:
                    not_chunked_text += '\n'
            not_chunked_text += f' ```'
        chunks = chunker(not_chunked_text, ' ```')
        for n, x in enumerate(chunks):
            if n == 0:
                await i.response.send_message(x)
            else:
                await i.followup.send(x)

    @app_commands.command(description='manual_description')
    async def manual(self, i: discord.Interaction):
        user = User(i.user.id, i.guild.id)
        await i.response.defer(ephemeral=True)
        if url := Server(i.guild.id).roc_server().get('manual_url', None):
            v = ManualView(user.get_localization(), url)
            await i.followup.send(content=v.get_content(), embed=v.get_embed(), view=v, ephemeral=True)
        else:
            await i.followup.send(content=get_localized_answer('generic_error', user.get_localization()), ephemeral=True)


async def setup(client):
    await client.add_cog(PoS(client))

