import sqlite3


class ChannelDB:
    def __init__(self, channelID):
        self.conn = sqlite3.connect(channelID + ".db")
        self.conn.executescript('''
        create table if not exists users (user_id integer primary key);
        create table if not exists user_sightings (
            sighting_id integer primary key autoincrement,
            user_id integer not null,
            foreign key (user_id) references users (user_id),
            name text not null,
            avatar text not null,
            unique(user_id, name, avatar),
        );
        create table if not exists messages (
            message_id integer primary key,
            contents text,
            timestamp text not null,
            sighting_id integer not null,
            foreign key (sighting_id) references user_sightings (sighting_id)
        );
        create table if not exists attachments (
            attachment_id integer primary key,
            filename text not null,
            message_id integer not null,
            foreign key (message_id) references messages (message_id)
        );
        ''')

    def add_messages(self, messages):
        users = [(x,) for x in set(x["sender_id"] for x in messages)]
        self.conn.executemany("insert or ignore into users (user_id) values (?);", users)
        sighting_ids = {}
        for user in users:
            sighting = next(x for x in messages if x["sender_id"] == user[0])
            self.conn.execute(
                "insert or ignore into user_sightings (user_id, name, avatar) values (?, ?, ?)",
                (sighting["sender_id"], sighting["sender_name"], sighting["sender_avatar"])
            )
            sighting_id = self.conn.execute(
                "select (sighting_id) from sightings where user_id==? order by sighting_id desc limit 1;",
                user
            ).next()[0]
            sighting_ids[user[0]] = sighting_id
        self.conn.executemany(
            "insert or ignore into messages (message_id, contents, timestamp, sighting_id) values (?, ?, ?, ?)",
            [(m["id"], m["text"], m["time"], sighting_ids[m["id"]]) for m in messages]
        )
        self.conn.executemany(
            "insert or ignore into attachments (attachment_id, filename, message_id) values (?, ?, ?)",
            [(att["id"], att["filename"], att["message_id"]) for att in
             (a for agroup in (m["attachments"] for m in messages if m["attachments"]) for a in agroup)]
        )


if __name__ == "__main__":
    cdb = ChannelDB("test")
    cdb.add_messages()
