import discord.utils
from pymongo import MongoClient
import os
m_client = MongoClient(os.environ.get('DB'))
db = m_client['pos_db']
users = db['users']
servers = db['servers']
locations = db['locations']
events = db['events']


class Server:
    def __init__(self, server_id):
        self.server_id = server_id
        self.server = self.roc_server()

    def roc_server(self):  # Read or create
        if server := servers.find_one({'id': self.server_id}):
            return server
        else:
            server.insert_one({
                'id': self.server,
                'local': 'ukr',
                'manual_url': None
            })
            return servers.find_one({'id': self.server_id})

    def set_manual_url(self, url: str):
        servers.find_one_and_update({'id': self.server_id}, {'$set': {'manual_url': url}})


class User:
    def __init__(self, user_id, server_id):
        self.user_id = user_id
        self.server_id = server_id
        self.user = self.roc_user()

    def roc_user(self):  # Read or create
        if user := users.find_one({'id': self.user_id}):
            return user
        else:
            loc = Server(self.server_id).roc_server()['local']
            users.insert_one({
                'id': self.user_id,
                'local': loc
            })
            return users.find_one({'id': self.user_id})

    def upd_user(self, new_user):
        pass

    def get_localization(self):
        return self.user['local']

    def set_localization(self, locale):
        users.update_one({'id': self.user_id}, {"$set": {'local': locale}})
        self.user = self.roc_user()


class Location:
    def __init__(self, role_id, guild_id):
        self.role_id = role_id
        self.guild_id = guild_id

    def roc_location(self):
        if location := locations.find_one({'id': self.role_id, 'guild_id': self.guild_id}):
            return location
        else:
            locations.insert_one({
                'id': self.role_id,
                'guild_id': self.guild_id,
                'attached_locations': []
            })
            return locations.find_one({'id': self.role_id, 'guild_id': self.guild_id})

    def remove_location(self, role_id, guild_id):
        for loc in locations.find({'guild_id': guild_id}):
            try:
                loc['attached_locations'].remove(role_id)
            except ValueError:
                pass
            self.update_attachments(loc['id'], guild_id, loc['attached_locations'])
        locations.delete_one({'id': role_id, 'guild_id': guild_id})

    @staticmethod
    def update_attachments(l_id, guild_id, new):
        locations.update_one({'id': l_id, 'guild_id': guild_id}, {"$set": {'attached_locations': new}})

    def update_image(self, image_url):
        self.roc_location()
        locations.update_one({'id': self.role_id, 'guild_id': self.guild_id}, {"$set": {'url': image_url}})

    def update_description(self, description, locale):
        loc = self.roc_location()
        if desc := loc.get('description', None):
            desc[locale] = description
        else:
            desc = {locale: description}

        locations.update_one({'id': self.role_id, 'guild_id': self.guild_id}, {"$set": {'description': desc}})

    def attach_or_detach(self, attach_id, guild_id):
        if attachment := locations.find_one({'id': attach_id, 'guild_id': guild_id}):
            pass
        else:
            attachment = Location(attach_id, guild_id).roc_location()

        if self.role_id in attachment['attached_locations']:  # detach
            attachment['attached_locations'].remove(self.role_id)
            locs = self.roc_location()['attached_locations']
            locs.remove(attach_id)
        else:  # attach
            attachment['attached_locations'].append(self.role_id)
            locs = self.roc_location()['attached_locations']
            locs.append(attach_id)
        self.update_attachments(attach_id, guild_id, attachment['attached_locations'])
        self.update_attachments(self.role_id, guild_id, locs)


class Event:
    def __init__(self, guild_id, weight=1., location_id=None, url=None):
        self.location_id = location_id
        self.guild_id = guild_id
        self.weight = weight
        self.url = url

    def roc_event(self, e_id=None):
        if event := events.find_one({'_id': e_id, 'guild_id': self.guild_id}):
            return event
        else:
            doc = events.insert_one({
                'location_id': self.location_id,
                'guild_id': self.guild_id,
                'localized_events': {},
                'statistical_weight': self.weight,
                'url': self.url
            })
            return events.find_one({'_id': doc.inserted_id, 'guild_id': self.guild_id})

    def remove_event(self, e_id):
        events.delete_one({'_id': e_id, 'guild_id': self.guild_id})

    def edit_event(self, e_id, new_event, locale):
        event = events.find_one({'_id': e_id, 'guild_id': self.guild_id})
        event['localized_events'][locale] = new_event
        print(event['localized_events'], new_event)
        events.update_one({'_id': e_id, 'guild_id': self.guild_id}, {"$set": {'localized_events': event['localized_events']}})

    def change_event_location(self, e_id, location=None):
        events.update_one({'_id': e_id, 'guild_id': self.guild_id}, {"$set": {'location_id': location}})

    def change_event_weight(self, e_id):
        events.update_one({'_id': e_id, 'guild_id': self.guild_id}, {"$set": {'statistical_weight': self.weight}})

    def change_event_url(self, e_id, url):
        events.update_one({'_id': e_id, 'guild_id': self.guild_id}, {"$set": {'url': url}})

