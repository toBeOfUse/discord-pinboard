import sqlite3

import channeldb_test_data
import os


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
            sighting_id integer,
            archival integer,
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

    def add_messages(self, messages, archival=False):
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
                (message_id, contents, timestamp, sighting_id, archival)
                values (?, ?, ?, ?, ?);''',
            [(m["id"], m["text"], m["time"], sighting_ids[m["sender_id"]], int(archival)) for m in messages]
        )
        self.conn.executemany(
            "insert or ignore into attachments (attachment_id, filename, message_id) values (?, ?, ?);",
            [(att["id"], att["filename"], att["message_id"]) for att in
             (a for agroup in (m["attachments"] for m in messages if m["attachments"]) for a in agroup)]
        )
        self.conn.commit()

    def close(self):
        self.conn.close()

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
    cdb.add_messages(channeldb_test_data.simplemessages)
    cdb.add_messages(channeldb_test_data.avatarchange)
    cdb.add_messages(channeldb_test_data.avatarandusernamechange)
    cdb.add_messages(channeldb_test_data.oldmessages, archival=True)
    print(cdb.dump())
    cdb.close()
    os.remove("test.db")
