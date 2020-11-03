import discord
import asyncio
from pprint import pprint

class PinsClient(discord.Client):
    def __init__(self, token):
        discord.Client.__init__(self)
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
        pins = await self.private_channels[channel_index].pins()
        return [self.message_to_dict(m) for m in pins]

async def test():
    with open("token.txt") as tokenfile:
        token = tokenfile.read()
        pc = PinsClient(token)
        await pc.connected
        dmchannels = pc.get_dm_channel_list()
        i = -1
        for i in range(len(dmchannels)):
            print(str(i+1)+". " + str(dmchannels[i]))
        while True:
            try:
                target = int(input("pick channel plz: "))
                if 0 < target <= len(dmchannels):
                    i = target - 1
                    break
            except:
                pass
            print("that is a not a good number try again")
        pprint(await pc.get_pins(i))

if __name__ == "__main__":
    asyncio.run(test())