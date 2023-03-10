import discord.app_commands
import numpy
from discord.ui import View, Button, Select
from discord import SelectOption, Interaction
from misc import chunker, get_localized_answer
import gspread
import gspread.utils

client = gspread.service_account('credentials.json')


async def followup_images(interaction, images, title=''):
    if images:
        for image in images:
            temp_emb = discord.Embed(title=title)
            temp_emb.set_image(url=image)
            await interaction.followup.send(embed=temp_emb, ephemeral=True)


class ManualSelect(Select):
    def __init__(self, initial_data):
        options = [SelectOption(label=name) for name, _ in initial_data]
        super().__init__(options=options)

    async def callback(self, interaction: Interaction):
        emb = discord.Embed()
        for key, value in self.view.data:
            emb.add_field(name=key, value=value[:100], inline=False)
        v = PaginatedBackView(self.view, emb, self.values[0], dict(self.view.data).get(self.values[0]))
        new_emb, images = v.get_embed()

        await interaction.response.edit_message(content=v.get_content(), view=v, embed=new_emb)
        await followup_images(interaction, images, v.key)

    def update_options(self):
        self.view.data = self.view.get_localized_paginated_list()
        self.options = [SelectOption(label=name) for name, _ in self.view.data]


class ManualView(View):
    def __init__(self, localization, spreadsheet_url, max_options=5, ):
        super().__init__()
        spreadsheet = client.open_by_url(spreadsheet_url)
        self.sheet = spreadsheet.worksheet('manual')
        self.locale = localization

        self.page = 0

        values = self.sheet.get_values(f'A2:C')
        self.max_options = max_options
        self.max_range = int(values[0][2])
        values = [[x, y] for x, y, _ in values]
        self.cell_coords = dict(values)
        self.data = self.get_localized_paginated_list()
        self.select = ManualSelect(self.data)
        self.add_item(self.select)
        self.opts = int(numpy.ceil(self.max_range / self.max_options))
        if self.opts > 1:
            self.add_item(PageChangeBTN(-1, self.opts, '<'))
            self.add_item(PageChangeBTN(1, self.opts, '>'))

    def get_localized_paginated_list(self):
        r, c = gspread.utils.a1_to_rowcol(self.cell_coords['default'])
        r_l, c_l = gspread.utils.a1_to_rowcol(self.cell_coords.get(self.locale, self.cell_coords['default']))
        r, r_l = r + self.page * self.max_options, r_l + self.page * self.max_options

        data, localized_data = self.sheet.batch_get([f'{gspread.utils.rowcol_to_a1(r, c)}:'
                                                     f'{gspread.utils.rowcol_to_a1(r + self.max_options - 1, c + 1)}',
                                                     f'{gspread.utils.rowcol_to_a1(r_l, c_l)}:'
                                                     f'{gspread.utils.rowcol_to_a1(r_l + self.max_options - 1, c_l + 1)}'])
        if self.locale != 'default' and self.locale in self.cell_coords.keys():
            localized_data = gspread.utils.fill_gaps(localized_data, len(data), 2)
            for n, (loc_dat, dat) in enumerate(zip(localized_data, data)):
                if not loc_dat[0] or not loc_dat[1]:
                    localized_data[n] = dat
            data = localized_data
        return data

    def get_embed(self):
        emb = discord.Embed()
        for key, _ in self.data:
            if len(key) > 256:
                key = key[:250] + '...'
            emb.add_field(name=key, inline=False, value='')
        return emb

    def get_content(self):
        if self.opts > 1:
            return f'{self.page + 1}/{self.opts}'
        return ''

    async def change_page(self, i: Interaction):
        await i.response.defer(ephemeral=True)
        sel = self.select
        self.remove_item(sel)
        self.select.update_options()
        self.add_item(sel)
        msg = await i.original_response()
        await msg.edit(content=self.get_content(), embed=self.get_embed(), view=self)


class PaginatedBackView(View):
    def __init__(self, original_view, emb, key, value):
        super().__init__()
        self.original_view = original_view
        if len(key) > 256:
            key = key[:250] + '...'

        self.key = key
        self.emb = emb
        self.page = 0
        self.chunked = chunker(value, '\n', 4096)
        self.add_item(BackBTN(get_localized_answer('back_btn_label', original_view.locale)))
        if len(self.chunked) > 1:
            self.add_item(PageChangeBTN(-1, len(self.chunked) - 1, '<'))
            self.add_item(PageChangeBTN(1, len(self.chunked) - 1, '>'))

    def get_embed(self):
        new_emb = discord.Embed(title=self.key, description='')
        images = []
        key_for_image = '{image_url='
        for x in range(0, self.chunked[self.page].count(key_for_image)):
            if self.chunked[self.page].count(key_for_image) >= 1 and self.chunked[self.page].count('}') >= 1:
                first_keyword = self.chunked[self.page].index(key_for_image)
                second_keyword = self.chunked[self.page].index('}')
                url = self.chunked[self.page][first_keyword + len(key_for_image):second_keyword]
                self.chunked[self.page] = self.chunked[self.page][:first_keyword] + self.chunked[self.page][
                                                                                    second_keyword + 1:]
                images.append(url)
        if images:
            new_emb.set_image(url=images.pop(0))

        if self.chunked[self.page]:
            new_emb.description = self.chunked[self.page]
        return new_emb, images

    def get_content(self):
        if len(self.chunked) > 1:
            return f'{self.page + 1}/{len(self.chunked)}'
        return ''

    async def change_page(self, interaction: Interaction):
        embed, images = self.get_embed()
        await interaction.response.edit_message(content=self.get_content(), embed=embed)
        await followup_images(interaction, images, self.key)


class BackBTN(Button):
    def __init__(self, label):
        super().__init__(label=label)

    async def callback(self, i: Interaction):
        await i.response.defer(ephemeral=True)
        msg = await i.original_response()
        await msg.edit(content=self.view.original_view.get_content(),
                       embed=self.view.original_view.get_embed(),
                       view=self.view.original_view)


class PageChangeBTN(Button):
    def __init__(self, move_dir, max_idx, emoji):
        super().__init__(label=emoji)
        self.move_dir = move_dir
        self.max_idx = max_idx

    async def callback(self, interaction: Interaction):
        self.view.page += self.move_dir
        self.view.page = int(numpy.clip(self.view.page, 0, self.max_idx))
        await self.view.change_page(interaction)
