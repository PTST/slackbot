from slackclient import SlackClient
import time
import uuid
import json
import os
from slackbot_functions import do
import ipgetter

script_dir = os.path.dirname(__file__)
script_dir = os.path.join(script_dir, "Resources")

with open(os.path.join(script_dir, "settings.json"), "r") as f:
    settings = json.load(f)

timestamp = settings["latest_ts"]
bot_token = settings["bot_token"]
user_token = settings["user_token"]
cur_ip = settings["ip"]
user_sc = SlackClient(user_token)
bot_sc = SlackClient(bot_token)

providers = {"postnord": "https://www.postnord.dk/api/shipment/", "gls": "https://gls-group.eu/app/service/open/rest/EU/en/rstt001?match=", "bring": "https://tracking.bring.com/api/v2/tracking.json?q="}

try:
    with open(os.path.join(script_dir, "orders.json"), "r") as f:
        orders = json.load(f)
except FileNotFoundError:
    orders = {}



should_restart = False
keys_to_delete = []
channels = do.get_channels(user_sc)
channel = channels["bot"]
do.post_message(bot_sc, "HEYOOO, i'm online again! :raised_hands:", channel)

"""
 /$$       /$$$$$$$$ /$$$$$$$$       /$$$$$$$$ /$$   /$$ /$$$$$$$$       /$$      /$$  /$$$$$$   /$$$$$$  /$$$$$$  /$$$$$$        /$$$$$$$  /$$$$$$$$  /$$$$$$  /$$$$$$ /$$   /$$
| $$      | $$_____/|__  $$__/      |__  $$__/| $$  | $$| $$_____/      | $$$    /$$$ /$$__  $$ /$$__  $$|_  $$_/ /$$__  $$      | $$__  $$| $$_____/ /$$__  $$|_  $$_/| $$$ | $$
| $$      | $$         | $$            | $$   | $$  | $$| $$            | $$$$  /$$$$| $$  \ $$| $$  \__/  | $$  | $$  \__/      | $$  \ $$| $$      | $$  \__/  | $$  | $$$$| $$
| $$      | $$$$$      | $$            | $$   | $$$$$$$$| $$$$$         | $$ $$/$$ $$| $$$$$$$$| $$ /$$$$  | $$  | $$            | $$$$$$$ | $$$$$   | $$ /$$$$  | $$  | $$ $$ $$
| $$      | $$__/      | $$            | $$   | $$__  $$| $$__/         | $$  $$$| $$| $$__  $$| $$|_  $$  | $$  | $$            | $$__  $$| $$__/   | $$|_  $$  | $$  | $$  $$$$
| $$      | $$         | $$            | $$   | $$  | $$| $$            | $$\  $ | $$| $$  | $$| $$  \ $$  | $$  | $$    $$      | $$  \ $$| $$      | $$  \ $$  | $$  | $$\  $$$
| $$$$$$$$| $$$$$$$$   | $$            | $$   | $$  | $$| $$$$$$$$      | $$ \/  | $$| $$  | $$|  $$$$$$/ /$$$$$$|  $$$$$$/      | $$$$$$$/| $$$$$$$$|  $$$$$$/ /$$$$$$| $$ \  $$
|________/|________/   |__/            |__/   |__/  |__/|________/      |__/     |__/|__/  |__/ \______/ |______/ \______/       |_______/ |________/ \______/ |______/|__/  \__/
"""
while True:
    with open(os.path.join(script_dir, "orders.json"), "w") as f:
        json.dump(orders, f)
    if settings["latest_ts"] != timestamp or settings["ip"] != cur_ip:
        settings["latest_ts"] = timestamp
        settings["ip"] = cur_ip
        with open(os.path.join(script_dir, "settings.json"), "w") as f:
            json.dump(settings, f)

    if should_restart:
        os.execl(os.path.join(script_dir, "reboot.sh"), '')

    cur_ip = ipgetter.myip()

    if settings["ip"] != cur_ip:
        do.post_message(bot_sc, "The robot IP changed to {0}".format(cur_ip), channel)

    for key, value in orders.items():
        for k, v in value.items():
            if k == "tracking":
                if v["last_updated"]+60 < time.time():
                    package_status, package_delivered = do.get_package(v["provider"], v["url"])
                    if package_status is None:
                        continue

                    if package_status == "404":
                        keys_to_delete.append(key)
                        do.post_message(bot_sc, ":{0}: {1} - Does not seem to be a valid package, please try again".format(v['provider'], v['tracking_no']), channel)
                        continue

                    if package_status[0] != v["status"]:
                        v["status"] = package_status[0]
                        do.post_message(bot_sc, ":{0}: {1} - {2}".format(v["provider"], v["tracking_no"], package_status[0]), channel)
                    if package_delivered:
                        do.post_message(bot_sc, ":{0}: {1} - This package has been delivered to you. I'll no longer track this package.".format(v["provider"], v["tracking_no"]), channel)
                        keys_to_delete.append(key)
                    v["last_updated"] = time.time()



    for key in keys_to_delete:
        orders.pop(key)

    keys_to_delete = []
    messages, timestamp = do.get_messages(user_sc, channel, timestamp)
    for msg in messages:

        if msg["user"] == "SkyNet Alpha":
            time.sleep(2)
            continue

        message = msg["message"].lower()
        if message == "--restart robot":
            do.post_message(bot_sc, "Restarting robot", channel)
            should_restart = True
            continue

        if message.startswith("orders"):
            if len(orders) == 0:
                do.post_message(bot_sc, "No active orders right now, wanna give me something to do? :raised_hands:", channel)
            else:
                do.post_message(bot_sc, "Current orders:\n{0}".format(orders), channel)
            continue

        if message.startswith("track"):
            params = msg["message"].lower().split(" ")
            params.pop(0)
            if len(params) != 2:
                do.post_message(bot_sc, "Wrong amount of paramaters.\nPlease format message as \"Tracking <provider> <tracking no>\"", channel)
                continue

            provider = params[0]
            tracking_no = params[1]
            if provider not in providers:
                do.post_message(bot_sc, "The first parameter should be the tracking provider.\nThe following providers are supported \"{0}\"".format(", ".join(list(providers.keys()))), channel)
                continue

            get_url = providers[provider] + tracking_no
            already_tracking = False

            for key, value in orders.items():
                for k, v in value.items():
                    if k == "tracking":
                        if v["tracking_no"] == tracking_no:
                            already_tracking = True
                        latest_status = v["status"]

            if already_tracking:
                do.post_message(bot_sc, "This package is already being tracked\nThe last status was:\n{0}".format(latest_status), channel)
            else:
                orders[str(uuid.uuid4())] = {"tracking":{"provider": provider, "tracking_no": tracking_no, "url": get_url, "status": "", "last_updated": 0}}
                do.post_message(bot_sc, "I'll start tracking this package and keep you updated on it. :package:", channel)
            continue

        if message.startswith("remove") or message.startswith("delete"):
            params = msg["message"].lower().split(" ")
            params.pop(0)
            if len(params) != 1:
                do.post_message(bot_sc, "Wrong amount of paramaters.\nPlease format message as \"Remove|Delete <order_id>\"", channel)
                continue
            order_id = params[0]
            if order_id == "--all":
                orders = {}
                do.post_message(bot_sc, "Removed all active orders :exclamation:", channel)
                continue
            if order_id not in orders:
                current_orders = "\n".join(list(orders.keys()))
                if len(orders) == 0:
                    do.post_message(bot_sc, "No active orders right now, wanna give me something to do? :raised_hands:", channel)
                else:
                    do.post_message(bot_sc, "Could not find order_id in orders, the following order_id are available:\n{0}".format(current_orders), channel)
                continue
            orders.pop(order_id)
            do.post_message(bot_sc, "{0} succesfully removed from orders :exclamation:".format(order_id), channel)
            continue

        if message.startswith("find"):
            params = message.split(" ")
            params.pop(0)
            room = "".join(params)

            do.post_message(bot_sc, "Just a second while i try and find that for you :satellite:", channel)

            existing_upload = do.check_for_file(user_sc, room)
            if existing_upload is not None:
                do.post_with_attachment(bot_sc, room.upper(), existing_upload, channel)
                continue

            filepath = do.find_room(room)
            if filepath is None:
                do.post_message(bot_sc, "Could not find \"{0}\", please ensure correct spelling of room no.".format(room), channel)
                continue
            do.upload_file(bot_sc, filepath, channel, room.upper())
            continue

        if message.startswith("kantine") or message.startswith("menu"):
            menu = do.get_menu()
            do.post_message(bot_sc, menu, channel)
            continue

        if message.strip() == "ip":
            do.post_message(bot_sc, "The current IP is {0}".format(cur_ip), channel)
            continue

        do.post_message(bot_sc, "Not a valid order :question:", channel)

    time.sleep(1)
