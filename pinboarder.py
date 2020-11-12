from discord import LoginFailure
import discordclient
import channeldb
from pathlib import Path
import argparse
import asyncio
import slugify

parser = argparse.ArgumentParser(description="download discord pins for a dm channel, accumulate them in a database"
                                             " file, and create a static html page that showcases them")
parser.add_argument("token", type=str, help="authentication token for your discord account or a path to a text file"
                                            " containing it")
parser.add_argument("channel", type=str, help="search term that will be used to find the dm channel by its title; e. g."
                                              " 'bob' for a dm with user bob#3453 or 'lamb' for a group dm titled"
                                              " 'lamb discussion'. if there are multiple matches for your term you'll"
                                              " be asked which one you want to select. terms can be multi-word if you"
                                              " put them in quotes (i. e. \"lamb discuss\")")
parser.add_argument("--save_to", "-s", type=str, help="path and filename that you want the html file to be saved to; the"
                                                     " default is [channel-name].html", metavar="path")
parser.add_argument("--backup_attachments", "-b", help="backup any attachments in the messages that are being saved to"
                                                      " ./backup; they will be used by the html file if they are kept"
                                                      " in the same relative path and the attachments stop being"
                                                      " available on discord", action="store_true")
parser.add_argument("--deep_scan", "-d", help="scans channel for messages that were pinned but have been unpinned, for"
                                             " the 'archives' section of the showcase. may take a fairly long time for"
                                             " channels with a lot of messages", action="store_true")
async def main():
    args = parser.parse_args()
    if Path(args.token).exists():
        with open(args.token) as token_file:
            token = token_file.read().strip()
    else:
        token = args.token.strip()
    print("token obtained, connecting to discord...")
    try:
        client = discordclient.PinsClient(token)
        await client.connected
    except LoginFailure:
        print("failed to log in with the provided token ("+token+")")
        return
    channels = client.get_dm_channel_list()
    matching_channels = [(i, x) for i, x in enumerate(channels) if args.channel in x]
    index = -1
    if len(matching_channels) == 0:
        print("no channels found for search term "+args.channel)
        return
    elif len(matching_channels) > 1:
        print("multiple matches found for search term "+args.channel)
        for j in range(len(matching_channels)):
            print(str(j+1)+". "+matching_channels[j][1]+"\n")
        while True:
            try:
                choice = int(input("please enter the number corresponding to one of the above: "))
                if 0 < choice <= len(matching_channels):
                    index = matching_channels[choice][0]
            except ValueError:
                pass
            print("that is not a valid number :(")
    else:
        print("found channel "+matching_channels[0][1])
        index = matching_channels[0][0]
    slug = slugify.slugify(channels[index])
    pins = await client.get_pins(index)
    db = channeldb.ChannelDB(slug, client.get_dm_channel_id(index))
    await db.add_messages(pins, args.backup_attachments)
    if args.deep_scan:
        old_pins = await client.old_pins_search(index)
        await db.add_messages(old_pins, args.backup_attachments, archival=True)
    output = db.get_json()
    with open("template.html") as template_file:
        template = template_file.read()
    html = template.replace("{{inject_dpbdata}}", output)
    output_path = args.save_to if args.save_to else slug+".html"
    with open(output_path, "w") as output_file:
        output_file.write(html)
    await db.close()
    print("successfully created "+output_path)


if __name__ == "__main__":
    asyncio.run(main())