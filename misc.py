import discord
from discord.app_commands import Choice
import os
from pymongo import MongoClient
from typing import List
m_client = MongoClient(os.environ.get('DB'))
db = m_client['pos_db']
languages = db['languages']
events = db['events']
import random


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
            sub_str = inp_str[inp_str.index("{") + 1:inp_str.index("}")]
            split_str = sub_str.split('=')
            var = split_str[0].lower().replace(' ', '')
            if var == 'rand_num':
                x, y = split_str[1].split('|')
                x, y = int(x.replace(' ', '')), int(y.replace(' ', ''))
                inp_str = inp_str.replace(sub_str, str(random.randint(x, y)))
            elif var == 'rand_list':
                list_of_values = split_str[1].split(',')
                inp_str = inp_str.replace(sub_str, random.choice(list_of_values))
            elif var == 'rand_w_list':
                list_of_values = split_str[1].split(',')
                values = []
                weights = []
                for val in list_of_values:
                    val = val.split('|')
                    values.append(val[0])
                    weights.append(float(val[1]))
                ch = random.choices(values, cum_weights=weights)
                inp_str = inp_str.replace(sub_str, str(ch[0]))

            inp_str = inp_str[:inp_str.index("{")] + inp_str[inp_str.index("{") + 1:]
            inp_str = inp_str[:inp_str.index("}")] + inp_str[inp_str.index("}") + 1:]
            return procces_event(inp_str)
        return inp_str
    except ValueError as exc:
        return exc

def chunker(inp_str):
    chunks = []
    not_chunked_text = inp_str

    while not_chunked_text:
        if len(not_chunked_text) <= 2000:
            chunks.append(not_chunked_text)
            break
        split_index = not_chunked_text.rfind("\n", 0, 2000)
        if split_index == -1:
            # The chunk is too big, so everything until the next newline is deleted
            try:
                not_chunked_text = not_chunked_text.split("\n", 1)[1]
            except IndexError:
                # No "\n" in not_chunked_text, i.e. the end of the input text was reached
                break
        else:
            chunks.append(not_chunked_text[:split_index + 1])
            not_chunked_text = not_chunked_text[split_index + 1:]
    return chunks
