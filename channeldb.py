import sqlite3
import aiohttp
import os
import asyncio
from urllib.parse import urlparse
from pathlib import Path

import channeldb_test_data


class ChannelDB:
    def __init__(self, channelID):
        self.channel = channelID
        self.session = aiohttp.ClientSession()
        self.conn = sqlite3.connect(channelID + ".db")
        self.conn.executescript('''
        create table if not exists users (user_id integer primary key);
        create table if not exists user_snapshots (
            snapshot_id integer primary key autoincrement,
            user_id integer not null,
            name text not null,
            avatar_url text not null,
            avatar_filename text not null,
            foreign key (user_id) references users (user_id)
        );
        create table if not exists messages (
            message_id integer primary key,
            contents text,
            timestamp text not null,
            snapshot_id integer,
            archival integer,
            foreign key (snapshot_id) references user_snapshots (snapshot_id)
        );
        create table if not exists attachments (
            attachment_id integer primary key,
            filename text not null,
            url text not null,
            message_id integer not null,
            foreign key (message_id) references messages (message_id)
        );
        ''')
        self.conn.commit()

    async def save_thing(self, url, path):
        async with self.session.get(url) as resp:
            with open(path, 'wb') as fd:
                while True:
                    chunk = await resp.content.read(1024*500)
                    if not chunk:
                        break
                    fd.write(chunk)

    # saves an avatar into the avatars folder if necessary and returns a future for the dl and its filename
    def save_avatar(self, url):
        avatar_filename = Path(urlparse(url).path).name
        avatar_path = Path.cwd() / "avatars"
        avatar_path.mkdir(parents=True, exist_ok=True)
        avatar_path /= avatar_filename
        if not Path(avatar_path).exists():
            return self.save_thing(url, avatar_path), avatar_filename
        else:
            future = asyncio.get_event_loop().create_future()
            future.set_result("no dl needed")
            return future, avatar_filename

    # saves an attachment into ./channel_id/attachment_id/filename and returns a future for the dl
    def save_attachment(self, channel_id, attachment_id, filename, url):
        path = Path.cwd() / str(channel_id) / str(attachment_id)
        if not path.exists():
            path.mkdir(parents=True)
        return self.save_thing(url, path / filename)

    async def add_messages(self, messages, archival=False):
        # list of futures representing remote resource-saving operations (for asyncio.gather)
        dlqueue = []
        cur = self.conn.cursor()
        # maps user ids onto the ids of the most recent snapshot of that user; used to link messages to snapshots
        snapshot_ids = {}
        users = [(x,) for x in set(x["sender_id"] for x in messages)]
        cur.executemany("insert or ignore into users (user_id) values (?);", users)
        for user in users:
            snapshot = next(x for x in messages if x["sender_id"] == user[0])
            cur.execute(
                '''select snapshot_id, name, avatar_url from user_snapshots 
                where user_id=? 
                order by snapshot_id desc
                limit 1;''',
                user
            )
            last_snapshot = cur.fetchone()
            # if the most recent snapshot of this user is different from how they currently look (or there is no last
            # snapshot) add a snapshot of them to the database and save their current avatar if we don't already have it
            if not last_snapshot or last_snapshot[1:3] != (snapshot["sender_name"], snapshot["sender_avatar"]):
                dl, avatar_filename = self.save_avatar(snapshot["sender_avatar"])
                dlqueue.append(dl)
                cur.execute(
                    "insert into user_snapshots (user_id, name, avatar_url, avatar_filename) values (?, ?, ?, ?);",
                    (snapshot["sender_id"], snapshot["sender_name"], snapshot["sender_avatar"], avatar_filename)
                )
                snapshot_id = cur.lastrowid
            # otherwise, the messages logically belong to the most recently saved snapshot for this user
            else:
                snapshot_id = last_snapshot[0]
            snapshot_ids[user[0]] = snapshot_id
        cur.executemany(
            # messages we already have are ignored bc their primary keys already exist, preventing their insertion
            '''insert or ignore into messages 
                (message_id, contents, timestamp, snapshot_id, archival)
                values (?, ?, ?, ?, ?);''',
            [(m["id"], m["text"], m["time"], snapshot_ids[m["sender_id"]], int(archival)) for m in messages]
        )
        # take each message's attachment group out of its dict and then flatten the groups into a list
        attachments = [att for att in
                       (a for agroup in (m["attachments"] for m in messages if m["attachments"]) for a in agroup)]
        for attachment in attachments:
            # here we explicitly check if we already have each attachment (unlike with messages) because we need to know
            # whether to save it into a file or not
            if not cur.execute("select 1 from attachments where attachment_id=?", (attachment["id"],)).fetchone():
                cur.execute(
                    "insert into attachments (attachment_id, filename, url, message_id) values (?, ?, ?, ?);",
                    (attachment["id"], attachment["filename"], attachment["url"], attachment["message_id"])
                )
                print("saving attachment "+attachment["filename"])
                dlqueue.append(
                    self.save_attachment(self.channel, attachment["id"], attachment["filename"], attachment["url"])
                )
        await asyncio.gather(*dlqueue)
        self.conn.commit()

    def close(self):
        self.conn.close()
        self.session.close()

    def dump(self):
        out = "users:\n"
        for user in self.conn.execute("select * from users;"):
            out += str(user) + "\n"
        out += "\nsnapshots:\n"
        for snapshot in self.conn.execute("select * from user_snapshots;"):
            out += str(snapshot) + "\n"
        out += "\nmessages:\n"
        for message in self.conn.execute("select * from messages;"):
            out += str(message) + "\n"
        out += "\nattachments:\n"
        for attachment in self.conn.execute("select * from attachments;"):
            out += str(attachment) + "\n"
        return out


async def test():
    cdb = ChannelDB("test")
    await cdb.add_messages(channeldb_test_data.simplemessages)
    await cdb.add_messages(channeldb_test_data.avatarchange)
    await cdb.add_messages(channeldb_test_data.avatarandusernamechange)
    await cdb.add_messages(channeldb_test_data.oldmessages, archival=True)
    print(cdb.dump())
    cdb.close()
    os.remove("test.db")

if __name__ == "__main__":
    asyncio.run(test())
