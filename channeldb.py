import sqlite3
import datetime


class ChannelDB:
    def __init__(self, channelID):
        self.conn = sqlite3.connect(channelID + ".db")
        self.conn.executescript('''
        create table if not exists users (user_id integer primary key);
        create table if not exists user_sightings (
            sighting_id integer primary key autoincrement,
            user_id integer not null,
            name text not null,
            avatar text not null,
            unique(user_id, name, avatar),
            foreign key (user_id) references users (user_id)
        );
        create table if not exists messages (
            message_id integer primary key,
            contents text,
            timestamp text not null,
            sighting_id integer not null,
            currently_pinned integer,
            foreign key (sighting_id) references user_sightings (sighting_id)
        );
        create table if not exists attachments (
            attachment_id integer primary key,
            filename text not null,
            message_id integer not null,
            foreign key (message_id) references messages (message_id)
        );
        ''')
        self.conn.commit()

    def add_messages(self, messages, currently_pinned=True):
        users = [(x,) for x in set(x["sender_id"] for x in messages)]
        self.conn.executemany("insert or ignore into users (user_id) values (?);", users)
        sighting_ids = {}
        for user in users:
            sighting = next(x for x in messages if x["sender_id"] == user[0])
            self.conn.execute(
                "insert or ignore into user_sightings (user_id, name, avatar) values (?, ?, ?);",
                (sighting["sender_id"], sighting["sender_name"], sighting["sender_avatar"])
            )
            self.conn.commit()
            sighting_id = self.conn.execute(
                "select (sighting_id) from user_sightings where user_id==? order by sighting_id desc limit 1;",
                user
            ).fetchone()[0]
            sighting_ids[user[0]] = sighting_id
        self.conn.executemany(
            '''insert or ignore into messages 
                (message_id, contents, timestamp, sighting_id, currently_pinned)
                values (?, ?, ?, ?);''',
            [(m["id"], m["text"], m["time"], sighting_ids[m["sender_id"]], int(currently_pinned)) for m in messages]
        )
        self.conn.executemany(
            "insert or ignore into attachments (attachment_id, filename, message_id) values (?, ?, ?);",
            [(att["id"], att["filename"], att["message_id"]) for att in
             (a for agroup in (m["attachments"] for m in messages if m["attachments"]) for a in agroup)]
        )
        self.conn.commit()

    def dump(self):
        out = "users:\n"
        for user in self.conn.execute("select * from users;"):
            out += str(user) + "\n"
        out += "\nsightings:\n"
        for sighting in self.conn.execute("select * from user_sightings;"):
            out += str(sighting) + "\n"
        out += "\nmessages:\n"
        for message in self.conn.execute("select * from messages;"):
            out += str(message) + "\n"
        out += "\nattachments:\n"
        for attachment in self.conn.execute("select * from attachments;"):
            out += str(attachment) + "\n"
        return out


if __name__ == "__main__":
    cdb = ChannelDB("test")
    cdb.add_messages([{'attachments': [{'filename': 'unknown.png',
                                        'id': 770583153134796800,
                                        'message_id': 770583153332060190,
                                        'url': 'https://cdn.discordapp.com/attachments/681936370242945038/770583153134796800/unknown.png'}],
                       'id': 770583153332060190,
                       'sender_avatar': 'https://cdn.discordapp.com/avatars/402326044872409100/85299428167603eee033d330c307f0c2.png?size=1024',
                       'sender_id': 402326044872409100,
                       'sender_name': 'GiantPredatoryMollusk',
                       'text': '',
                       'time': datetime.datetime(2020, 10, 27, 9, 42, 20, 497000)},
                      {'attachments': [],
                       'id': 769443495755644958,
                       'sender_avatar': 'https://cdn.discordapp.com/avatars/338261686014181377/ce561e6a9c1bf43921cca5dc93765f20.png?size=1024',
                       'sender_id': 338261686014181377,
                       'sender_name': 'Cassie',
                       'text': 'u have no idea how much I mean to me',
                       'time': datetime.datetime(2020, 10, 24, 6, 13, 44, 957000)},
                      {'attachments': [],
                       'id': 769440108717015073,
                       'sender_avatar': 'https://cdn.discordapp.com/avatars/338261686014181377/ce561e6a9c1bf43921cca5dc93765f20.png?size=1024',
                       'sender_id': 338261686014181377,
                       'sender_name': 'Cassie',
                       'text': "I did rocking horse and they were just like 'fucking a horse'???",
                       'time': datetime.datetime(2020, 10, 24, 6, 0, 17, 424000)},
                      {'attachments': [],
                       'id': 769440035107373076,
                       'sender_avatar': 'https://cdn.discordapp.com/avatars/338261686014181377/ce561e6a9c1bf43921cca5dc93765f20.png?size=1024',
                       'sender_id': 338261686014181377,
                       'sender_name': 'Cassie',
                       'text': "I'm Too Drink for charades ??????????",
                       'time': datetime.datetime(2020, 10, 24, 5, 59, 59, 874000)}])
    print(cdb.dump())
