import sqlite3
import aiohttp
import os
import asyncio
import mimetypes
from urllib.parse import urlparse
import base64
from pathlib import Path
from pprint import PrettyPrinter, pformat, pprint
import json

import channeldb_test_data

PrettyPrinter._dispatch[bytes.__repr__] = \
    lambda self, object, stream, indent, allowance, context, level: stream.write("~bytes~")


def str_row(row):
    return pformat(tuple(row), compact=True, width=200)[0:300]


def print_row(row):
    print(str_row(row))


class ChannelDB:
    def __init__(self, channel_name, channel_id):
        self.channel_name = channel_name
        self.channel_id = channel_id
        self.session = aiohttp.ClientSession()
        self.conn = sqlite3.connect(channel_id + ".db")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript('''
        create table if not exists users (user_id integer primary key);
        create table if not exists user_snapshots (
            snapshot_id integer primary key autoincrement,
            user_id integer not null,
            name text not null,
            avatar_url text not null,
            foreign key (user_id) references users (user_id),
            unique(user_id, name, avatar_url)
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
        create table if not exists avatars (
            avatar_url text primary key,
            avatar blob not null
        );
        ''')
        self.conn.commit()

    # saves an avatar into the avatars table if necessary
    async def save_avatar(self, url):
        if not self.conn.execute("select 1 from avatars where avatar_url=?;", (url,)).fetchone():
            self.conn.execute("insert into avatars (avatar_url, avatar) values (?, 'placeholder')", (url,))
            async with self.session.get(url) as resp:
                avatar = await resp.read()
                self.conn.execute("update avatars set avatar=? where avatar_url=?", (avatar, url))

    # saves an attachment into ./backup/channel_name/attachment_id/filename and returns a future for the dl
    def save_attachment(self, attachment_id, filename, url):
        path = Path.cwd() / "backup" / self.channel_name / str(attachment_id)
        if not path.exists():
            path.mkdir(parents=True)
        return self.save_thing(url, path / filename)

    async def save_thing(self, url, path):
        async with self.session.get(url) as resp:
            with open(path, 'wb') as fd:
                while True:
                    chunk = await resp.content.read(1024 * 500)
                    if not chunk:
                        break
                    fd.write(chunk)

    async def add_messages(self, messages, save_attachments, archival=False):
        # list of futures representing asset-retrieval operations (for asyncio.gather)
        dlqueue = []
        cur = self.conn.cursor()
        # maps user ids onto the ids of the most recent snapshot of that user; used to link messages to snapshots
        snapshot_ids = {}
        users = [(x,) for x in set(x["sender_id"] for x in messages)]
        cur.executemany("insert or ignore into users (user_id) values (?);", users)
        for user in users:
            snapshot = next(x for x in messages if x["sender_id"] == user[0])
            cur.execute(
                '''select snapshot_id from user_snapshots 
                where user_id=? and name=? and avatar_url=?
                limit 1;''',
                (snapshot["sender_id"], snapshot["sender_name"], snapshot["sender_avatar"])
            )
            matching_snapshot = cur.fetchone()
            # we need the id of the snapshot that represents the current state of this user, whether we are just
            # inserting the snapshot (first case handled) or it is already there (second case)
            if not matching_snapshot:
                dlqueue.append(self.save_avatar(snapshot["sender_avatar"]))
                cur.execute(
                    "insert into user_snapshots (user_id, name, avatar_url) values (?, ?, ?);",
                    (snapshot["sender_id"], snapshot["sender_name"], snapshot["sender_avatar"])
                )
                snapshot_id = cur.lastrowid
            else:
                snapshot_id = matching_snapshot["snapshot_id"]
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
                if save_attachments:
                    print("saving attachment " + attachment["filename"])
                    dlqueue.append(
                        self.save_attachment(attachment["id"], attachment["filename"], attachment["url"])
                    )
        await asyncio.gather(*dlqueue)
        self.conn.commit()

    def get_dict(self):
        cur = self.conn.cursor()
        snapshot_dict = {}
        cur.execute("select user_id from users;")
        for user in cur:
            snapshots = self.conn.execute(
                "select snapshot_id, user_id, name, avatar_url from user_snapshots where user_id=?;", (user[0],)
            ).fetchall()
            snapshot_dict[user["user_id"]] = [dict(x) for x in snapshots]
        avatar_dicts = []
        cur.execute("select avatar_url, avatar from avatars;")
        for avatar in cur:
            mime = mimetypes.guess_type(urlparse(avatar["avatar_url"]).path)
            avatar_dicts.append(
                {avatar["avatar_url"]:
                     "data:" + mime[0] + ";base64," + str(base64.b64encode(avatar["avatar"]), encoding="utf-8")}
            )
        message_dicts = []
        archived_message_dicts = []
        cur.execute("select message_id, contents, timestamp, snapshot_id, archival from messages;")
        for message in cur:
            dm = (dict(message))
            user_id = self.conn.execute(
                "select user_id from user_snapshots where snapshot_id=? limit 1;", (message["snapshot_id"],)
            ).fetchone()[0]
            dm["user_id"] = user_id
            dm["attachments"] = []
            for attachment in self.conn.execute(
                    "select url, filename, attachment_id from attachments where message_id=?;", (message["message_id"],)
            ):
                dm["attachments"].append(dict(attachment))
            if dm["archival"]:
                archived_message_dicts.append(dm)
                del archived_message_dicts[-1]["archival"]
            else:
                message_dicts.append(dm)
                del message_dicts[-1]["archival"]
        return {"messages": message_dicts, "archived_messages": archived_message_dicts, "avatars": avatar_dicts,
                "users": snapshot_dict, "channel_id": self.channel_id}

    def get_json(self):
        return json.dumps(self.get_dict())

    async def close(self):
        self.conn.close()
        await self.session.close()

    def dump(self):
        out = "users:\n"
        for user in self.conn.execute("select * from users;"):
            out += str_row(user) + "\n"
        out += "\navatars:\n"
        for avatar in self.conn.execute("select * from avatars;"):
            out += str_row(avatar) + "\n"
        out += "\nsnapshots:\n"
        for snapshot in self.conn.execute("select * from user_snapshots;"):
            out += str_row(snapshot) + "\n"
        out += "\nmessages:\n"
        for message in self.conn.execute(
                '''select timestamp, name, avatar_url, contents, archival from messages
                left join user_snapshots using(snapshot_id);'''
        ):
            out += str_row(message) + "\n"
        out += "\nattachments:\n"
        for attachment in self.conn.execute("select * from attachments;"):
            out += str_row(attachment) + "\n"
        return out


async def test():
    try:
        cdb = ChannelDB("test")
        await cdb.add_messages(channeldb_test_data.simplemessages)
        await cdb.add_messages(channeldb_test_data.avatarchange)
        await cdb.add_messages(channeldb_test_data.avatarandusernamechange)
        await cdb.add_messages(channeldb_test_data.oldmessages, archival=True)
        print(cdb.dump())
        pprint(cdb.get_dict(), width=200)
        await cdb.close()
    except Exception as e:
        print(e)
        pass
    os.remove("test.db")


if __name__ == "__main__":
    asyncio.run(test())
