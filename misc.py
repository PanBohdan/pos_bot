import discord
from discord.app_commands import Choice
import os
from pymongo import MongoClient
from typing import List
import random

m_client = MongoClient(os.environ.get('DB'))
db = m_client['pos_db']
languages = db['languages']
events = db['events']


async def set_locale_autocomplete(interaction: discord.Interaction, current: str, ) -> List[Choice[str]]:
    choices = [x['language'] for x in languages.find()]
    return [
        Choice(name=choice, value=choice)
        for choice in choices if current.lower() in choice.lower()
    ]


async def get_location_autocomplete(interaction: discord.Interaction, current: str) -> List[Choice[str]]:
    choices = [str(x['_id']) for x in events.find({'guild_id': interaction.guild_id})]
    return [
        Choice(name=choice, value=choice)
        for choice in choices if current in choice
    ]



def procces_event(inp_str: str) -> object:
    try:
        if inp_str.count('{') >= 1 and inp_str.count('}') >= 1:
            sub_str = inp_str[inp_str.rindex("{") + 1:inp_str.rindex("}")]
            split_str = sub_str.split('=')
            var = split_str[0].lower().replace(' ', '').lstrip().rstrip()
            if var == 'rand_num':
                x, y = split_str[1].split('|')
                x, y = int(x.replace(' ', '')), int(y.replace(' ', ''))
                inp_str = inp_str[:inp_str.rindex("{")] + str(random.randint(x, y)) + inp_str[inp_str.rindex("}")+1:]

            elif var == 'rand_list':
                list_of_values = split_str[1].split(',')
                for n, value in enumerate(list_of_values):
                    list_of_values[n] = value.lstrip().rstrip()
                inp_str = inp_str[:inp_str.rindex("{")] + random.choice(list_of_values) + inp_str[inp_str.rindex("}")+1:]
            elif var == 'rand_w_list':
                list_of_values = split_str[1].split(',')
                values = []
                weights = []
                for val in list_of_values:
                    val = val.split('|')
                    val[0] = val[0].lstrip().rstrip()
                    values.append(val[0])
                    weights.append(float(val[1]))
                ch = random.choices(values, weights=weights)
                inp_str = inp_str[:inp_str.rindex("{")] + ch[0] + inp_str[inp_str.rindex("}")+1:]
            return procces_event(inp_str)
        return inp_str
    except ValueError as exc:
        return exc


def chunker(inp_str, chunk_str='\n'):
    chunks = []
    not_chunked_text = inp_str

    while not_chunked_text:
        if len(not_chunked_text) <= 2000:
            chunks.append(not_chunked_text)
            break
        split_index = not_chunked_text.rfind(chunk_str, 0, 2000)
        if split_index == -1:
            # The chunk is too big, so everything until the next newline is deleted
            try:
                not_chunked_text = not_chunked_text.split(chunk_str, 1)[1]
            except IndexError:
                # No "\n" in not_chunked_text, i.e. the end of the input text was reached
                break
        else:
            chunks.append(not_chunked_text[:split_index + 1])
            not_chunked_text = not_chunked_text[split_index + 1:]
    return chunks
