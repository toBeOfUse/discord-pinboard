import discord
import asyncio
from pprint import pprint

class PinsClient(discord.Client):
    def __init__(self, token, status_report=print):
        discord.Client.__init__(self)
        self.set_status = status_report
        self.connected = asyncio.get_event_loop().create_future()
        asyncio.create_task(self.start(token, bot=False))

    async def on_connect(self):
        self.connected.set_result("connected")

    def get_dm_channel_list(self):
        return [str(c) for c in self.private_channels]

    @staticmethod
    def message_to_dict(m):
        return {
            "id": m.id,
            "sender_name": m.author.name,
            "sender_id": m.author.id,
            "sender_avatar": str(m.author.avatar_url_as(static_format="png")),
            "text": m.clean_content,
            "time": m.created_at,
            "attachments": [
                {"id": a.id, "filename": a.filename, "url": a.url, "message_id": m.id} for a in m.attachments
            ]
        }

    async def get_pins(self, channel_index):
        self.set_status("loading pins...")
        pins = await self.private_channels[channel_index].pins()
        self.set_status("processing pins...")
        return [self.message_to_dict(m) for m in pins]

    async def old_pins_search(self, channel_index, extra_ids=()):
        found_pin_ids = set()
        extra_pin_ids = set(extra_ids)
        pins = []
        extra_pins = []
        scanned = 0
        found = 0
        async for message in self.private_channels[channel_index].history(limit=None):
            scanned += 1
            if message.type == discord.MessageType.pins_add:
                found_pin_ids.add(message.reference.message_id)
            elif message.id in extra_pin_ids:
                pins.append(self.message_to_dict(message))
            elif message.type == discord.MessageType.default and message.id in found_pin_ids and not message.pinned:
                pins.append(self.message_to_dict(message))
                found += 1
            if scanned % 1000 == 0:
                self.set_status("scanned "+str(scanned)+" messages, found "+str(found)+" formerly pinned messages")
        self.set_status(str(len(found_pin_ids)-found)+" formerly pinned messages not found; probably deleted")
        if not extra_ids:
            return pins
        else:
            self.set_status(str(len(extra_pins))+" found out of "+str(len(extra_ids))+" requested")
            return pins, extra_pins


async def test():
    with open("token.txt") as tokenfile:
        token = tokenfile.read()
        pc = PinsClient(token)
        await pc.connected
        dmchannels = pc.get_dm_channel_list()
        for j in range(len(dmchannels)):
            print(str(j+1)+". " + str(dmchannels[j]))
        while True:
            try:
                target = int(input("pick channel plz: "))
                if 0 < target <= len(dmchannels):
                    i = target - 1
                    break
            except ValueError:
                pass
            print("that is a not a good number try again")
        print("fetching current pins...")
        pprint(await pc.get_pins(i))
        print("\nfetching archival pins...")
        pprint(await pc.old_pins_search(i))


if __name__ == "__main__":
    asyncio.run(test())
