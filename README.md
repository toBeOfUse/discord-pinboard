# Pinboard for Discord: Preserve and Showcase Discord Pins and Channel History Long-Term

Discord allows users to "pin" messages to a small showcase in text chat channels, but limits the number of allowed pinned messages to 50. This tool enhances the "pins" functionality by scanning a DM channel's pins an unlimited number of times to create and maintain an HTML file that acts as a showcase for all of the pinned messages ever picked up by the scan; additionally, it records the names and avatars of users at the time of the scan and preserves them in the record, it can back up attachments shown in the pinned messages in case they're ever deleted, and can conduct a full-channel search to pick up messages that were pinned at any point in the past to display a fuller channel history.

## Feature by feature:
 - Logs in to Discord using your personal authentication token, which is a very convenient login method unfortunately forbidden by the Discord terms of use but harmless at least for the moment. OAuth2 login coming soon. [Learn how to obtain your token here.](https://discordhelp.net/discord-token)
  - Stores each scanned channel's information in a SQLite3 database, which can be moved from computer to computer just by copying and pasting a .db file
  - Generates a single HTML showcase file that contains all information needed to display your pins except the attachments, which are fetched from the Discord CDN for display
  - Can optionally back up all relevant attachment files
  - Can search a channel for "[user] has pinned a message to the channel" notifications, which are then traced to find removed pins dating back to the start of the channel which are then placed in an "Archives" section
  - Also accepts a list of message IDs for not-currently-pinned messages that the user wants to elevate from the flotsam and lagan in the archives; these go in a seperate "preserved" section in the showcase

## Installation:
1. You must have Python 3.5+ installed; use the latest version for the best results.
2. Create a virtual environment for the project by running `python -m venv ./venv/`.
3. Activate the virtual environment by running `./venv/Scripts/activate` on Windows or `source venv/Scripts/activate` on Linux.
4. Install the project's dependencies by running `python -m pip install requirements.txt`
5. You should now be able to run `python pinboarder.py` with the arguments detailed below. (Step 3, activating the program's virtual environment, will be necessary before running the program every time you open a new terminal to do so in the future.)

## Detailed Usage:
```
pinboarder.py [-h] [--save_to path] [--backup_attachments]
                     [--provide_ids json_or_path] [--deep_scan] [--use_cache]
                     token channel

download discord pins for a dm channel, accumulate them in a database file,
and create a static html page that showcases them.

positional arguments:
  token                 authentication token for your discord account or a
                        path to a text file containing it
  channel               search term that will be used to find the dm channel
                        by its title; e. g. 'bob' for a dm with user bob#3453
                        or 'lamb' for a group dm titled 'lamb discussion'. if
                        there are multiple matches for your term you'll be
                        asked which one you want to select. terms can be
                        multi-word if you put them in quotes (i. e. "lamb
                        discuss")

optional arguments:
  -h, --help            show this help message and exit
  --save_to path, -s path
                        path and filename that you want the html file to be
                        saved to; the default is [channel-name].html
  --backup_attachments, -b
                        backup any attachments in the messages that are being
                        saved to ./backup
  --provide_ids json_or_path, -p json_or_path
                        either a json array containing the ids of messages for
                        the 'preserved' section of the showcase (as strings or
                        ints) or the path to a json file containing such an
                        array. it may take a fairly long time to find these
                        messages if the channel has a lot of messages and/or
                        the messages are located fairly far back in its
                        history.
  --deep_scan, -d       scans channel for messages that were pinned but have
                        been unpinned, for the 'archives' section of the
                        showcase. may take a fairly long time for channels
                        with a lot of messages
  --use_cache, -u       debug option for just recreating the html page from
                        data in the relevant SQLite DB

Very simple example:
python pinboarder.py asdlSLKFDKSLsdlkfsjlk bob

Complex example:
python pinboarder.py asdlSLKFDKSLsdlkfsjlk bob -b -s bob.html -d -p [32948234843,3484398349,348993484389]

(Neither of the examples above will work ever because the token is not a real token but you get the idea)

```

## Features in Progress (at least in my head)
 - Official OAuth2 login
 - AES encryption for the data in the HTML file so that it's only readable to people with a passphrase
 - Letting the user specify the path a specific SQLite database file to use for a given channel
 - The ability to scan server channels as well as DM channels
 - Using backed-up attachments as fallbacks in the showcase HTML file if the file is absent from the Discord CDN
 - Better directory structure for storing output files
 - Let users choose which among the pins, preserved pins, and archived pins sections they want to be displayed in the output file
