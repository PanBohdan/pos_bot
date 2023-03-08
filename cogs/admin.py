import asyncio
import datetime

import discord.ext.commands
from discord.ext import commands
from discord import app_commands, Interaction
from discord.ui import View, Button
from db_clases import User, Server
from misc import get_localized_answer, chunker
import io


class Admin(commands.GroupCog, name="admin"):
    def __init__(self, client):
        self.client: discord.Client = client
        super().__init__()

    @app_commands.command(description='set_manual_url_description')
    async def set_manual_url(self, i: Interaction, url: str):
        user = User(i.user.id, i.guild.id)
        Server(i.guild.id).set_manual_url(url)
        await i.response.send_message(content=get_localized_answer('set_manual_url', user.get_localization()))

    @app_commands.command(description='votum_description')
    async def votum(self, i: Interaction, text: str, ping: bool, seconds: int, minutes: int = 0, hours: int = 0, days: int = 0):
        await i.response.defer()
        v = VotumView(text,
                      datetime.timedelta(seconds=seconds, minutes=minutes, hours=hours, days=days).total_seconds(),
                      i.user.id, i.guild.id, self.client, ping)
        await i.followup.send(content=v.get_str(), view=v)


class VoteButton(Button):
    def __init__(self, label, style, vote_yes, emoji=''):
        super().__init__(style=style, label=label, emoji=emoji)
        self.vote_yes = vote_yes

    async def callback(self, interaction: Interaction):
        user = User(interaction.user.id, interaction.guild.id)
        localization = user.get_localization()
        if interaction.user.id in self.view.voters:
            await interaction.response.send_message(content=get_localized_answer('vote_error', localization),
                                                    ephemeral=True)
        else:
            if self.vote_yes:
                self.view.votes_yes += 1
            else:
                self.view.votes_no += 1
            self.view.voters.append(interaction.user.id)
            await interaction.response.edit_message(content=self.view.get_str())
            await interaction.followup.send(content=get_localized_answer('vote_counted', localization),
                                            ephemeral=True)


class StartTimeButton(Button):
    def __init__(self, label, style):
        super().__init__(style=style, label=label)

    async def callback(self, interaction: Interaction):
        self.view.remove_item(self)
        await interaction.response.edit_message(view=self.view)
        await self.view.closer(interaction.channel_id, interaction.message.id)


class VotumView(View):
    def __init__(self, text, timer, user_id, server_id, client: discord.Client, ping):
        super().__init__(timeout=None)
        self.user = User(user_id, server_id)
        self.localization = self.user.get_localization()
        self.text = text
        self.ping = ping
        self.votes_yes, self.votes_no = 0, 0
        self.voters = []
        self.add_item(VoteButton('', discord.ButtonStyle.green, True, '✔'))
        self.add_item(VoteButton('', discord.ButtonStyle.red, False, '✖'))
        self.timer = timer
        self.add_item(StartTimeButton(get_localized_answer('start_timer', self.user.get_localization()), discord.ButtonStyle.blurple))
        self.yay = get_localized_answer('yay', self.localization)
        self.nay = get_localized_answer('nay', self.localization)
        self.client = client

    def get_str(self):
        return f"{self.text}\n\n{self.yay} - {self.votes_yes} | {self.nay} - {self.votes_no}"

    async def closer(self, channel_id, message_id):
        await asyncio.sleep(self.timer)
        msg: discord.Message = await self.client.get_channel(channel_id).fetch_message(message_id)
        await msg.edit(view=None)
        if self.ping:
            voters = ''
            for voter in self.voters:
                voters += msg.guild.get_member(voter).mention + '\n'
            chunks = chunker(
                f'{get_localized_answer("votum_closed", self.localization).format(num_of_users=len(self.voters))}\n {voters}')
            for chunk in chunks:
                await msg.reply(content=chunk)

        else:
            voters = ''
            for voter in self.voters:
                voters += str(msg.guild.get_member(voter)) + '\n'

            with io.StringIO(voters) as string_buffer:
                await msg.reply(content=f'{get_localized_answer("votum_closed", self.localization).format(num_of_users=len(self.voters))}',
                                file=discord.File(string_buffer, filename='votes.txt'))


async def setup(client):
    await client.add_cog(Admin(client))
