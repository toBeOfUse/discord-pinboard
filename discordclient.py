import discord
import asyncio

class PinsClient(discord.Client):
    def __init__(self, token):
        discord.Client.__init__(self)
        self.connected = asyncio.get_running_loop().create_future()
        asyncio.create_task(self.start(token, bot=False))

    async def on_connect(self):
        self.connected.set_result("connected")

    def get_channels(self):
        return "\n".join([str(c) for c in self.private_channels])

    @staticmethod
    def message_to_dict(m):
        return {
            "id": m.id,
            "sender_name": m.author.name,
            "sender_id": m.author.id,
            "sender_avatar": str(m.author.avatar_url_as(static_format="png")),
            "text": m.clean_content,
            "time": m.created_at,
            "attachments": [a.url for a in m.attachments]
        }

    async def get_pins(self, channel_index):
        pins = await self.private_channels[channel_index].pins()
        return [self.message_to_dict(m) for m in pins]

if __name__ == "__main__":
    with open("token.txt") as tokenfile:
        token = tokenfile.read()
        pc = PinsClient(token)
