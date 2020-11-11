from discord import LoginFailure
import discordclient
import channeldb
from pathlib import Path
import argparse
import asyncio

parser = argparse.ArgumentParser(description="download discord pins for a dm channel and create a static html page"
                                             " that showcases them")
parser.add_argument("token", type=str, help="authentication token for your discord account or a path to a text file"
                                            " containing it")
parser.add_argument("channel", type=str, help="search term that will be used to find the dm channel by its title; e. g."
                                              " 'bob' for a dm with user bob#3453 or 'lamb' for a group dm titled"
                                              " 'lamb discussion'. if there are multiple matches for your term you'll"
                                              " be asked which one you want to select. terms can be multi-word if you"
                                              " put them in quotes (i. e. \"lamb discuss\")")
parser.add_argument("-save_to", "-s", type=str, help="path and filename that you want the html file to be saved to; the"
                                                     " default is [channel-name].html")
parser.add_argument("-backup_attachments", "-b", help="backup any attachments in the messages that are being saved to"
                                                      " ./backup; they will be used by the html file if they are kept"
                                                      " in the same relative path and the attachments stop being"
                                                      " available on discord", action="store_true")
parser.add_argument("-deep_scan", "-d", help="scans channel for messages that were pinned but have been unpinned, for"
                                             " the 'archives' section of the showcase. may take a fairly long time for"
                                             " channels with a lot of messages", action="store_true")
async def goforit():
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




if __name__ == "__main__":
    asyncio.run(goforit())