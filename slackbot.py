from slackclient import SlackClient
import time
import uuid
import requests
import json
import os

script_dir = os.path.dirname(__file__)

def post_message(sc, message, channel):
    sc.api_call("chat.postMessage", channel=channel,
                text=message, username="SkyNet Alpha",
                icon_emoji=":robot_face:")

def get_channels(sc):
    channels = {}
    data = sc.api_call("channels.list")
    for item in data["channels"]:
        channels[item["name"]] = item["id"]
    return channels

def get_messages(sc, channel_id, ts):
    messages = []
    timestamps = []
    data = sc.api_call("channels.history", channel=channel_id, oldest=ts)
    if len(data["messages"]) > 0:
        for item in data["messages"]:
            if "bot_id" not in item:
                messages.append({"user": item["user"], "message": item["text"]})
            timestamps.append(float(item["ts"]))
        latest_ts = str(max(timestamps)+0.5)

    else:
        latest_ts = ts

    return messages, latest_ts

def post_confirm_message(sc, message, channel):
    sc.api_call("chat.postMessage",
                channel=channel,
                text=message,
                username="SkyNet Alpha",
                icon_emoji=":robot_face:",
                attachments=[{"text": "Are you sure you want to delete this order?",
                            "callback_id": "12312",
                            "attachment_type": "default",
                            "actions": [{"name": "confirm",
                                        "text": "Yes",
                                        "type": "button",
                                        "value": "yes",
                                        "confirm": {"title": "Are you sure?",
                                                    "text": "Are you completely sure?",
                                                    "ok_text": "Yes",
                                                    "dismiss_text": "No"}},
                                        {"name": "confirm",
                                        "text": "No",
                                        "type": "button",
                                        "value": "No"}]}])


def get_latest_message(sc, channel_id):
    message = {}
    data = sc.api_call("channels.info", channel=channel_id)
    if "username" not in data["channel"]["latest"]:
        message["user"] = data["channel"]["latest"]["user"]
    else:
        message["user"] = data["channel"]["latest"]["username"]
    message["message"] = data["channel"]["latest"]["text"]
    return message

def get_package(provider, url):
    try:
        if provider == "gls":
            delivered = False
            return_data = []
            r = requests.get(url)
            data = r.json()["tuStatus"][0]["history"]
            delivered = (r.json()["tuStatus"][0]["progressBar"]["statusInfo"].lower() == "delivered")
            for item in data:
                return_data.append("{0} {1} - {2}".format(item["date"], item["time"], item["evtDscr"]))
            return(return_data, delivered)

        if provider == "postnord":
            delivered = False
            return_data = []
            r = requests.get(url)
            data = r.json()["response"]["trackingInformationResponse"]["shipments"][0]["items"][0]["events"]
            delivered = (r.json()["response"]["trackingInformationResponse"]["shipments"][0]["status"].lower() == "delivered")
            for item in data:
                return_data.append("{0} - {1}".format(item["eventTime"].replace("T", " "), item["eventDescription"]))
            return(return_data, delivered)
    except Exception:
        return(None, False)


with open(os.path.join(script_dir, "settings.json"), "r") as f:
    settings = json.load(f)

timestamp = settings["latest_ts"]
token = settings["token"]
sc = SlackClient(token)

providers = {"postnord": "https://www.postnord.dk/api/shipment/", "gls": "https://gls-group.eu/app/service/open/rest/EU/en/rstt001?match="}

try:
    with open(os.path.join(script_dir, "orders.json"), "r") as f:
        orders = json.load(f)
except FileNotFoundError:
    orders = {}

keys_to_delete = []
channels = get_channels(sc)
channel = channels["bot"]
post_message(sc, "HEYOOO, i'm online again! :raised_hands:", channel)

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
    if settings["latest_ts"] != timestamp:
        settings["latest_ts"] = timestamp
        with open(os.path.join(script_dir, "settings.json"), "w") as f:
            json.dump(settings, f)

    for key, value in orders.items():
        for k, v in value.items():
            if k == "tracking":
                if v["last_updated"]+60 < time.time():
                    package_status, package_delivered = get_package(v["provider"], v["url"])
                    if package_status is None:
                        continue
                    if package_status[0] != v["status"]:
                        v["status"] = package_status[0]
                        post_message(sc, ":{0}: {1} - {2}".format(provider, tracking_no, package_status[0]), channel)
                    if package_delivered:
                        post_message(sc, ":{0}: {1} - This package has been delivered to you. I'll no longer track this package.".format(provider, tracking_no), channel)
                        keys_to_delete.append(key)
                    v["last_updated"] = time.time()



    for key in keys_to_delete:
        orders.pop(key)

    keys_to_delete = []

    messages, timestamp = get_messages(sc, channel, timestamp)
    for msg in messages:

        if msg["user"] == "SkyNet Alpha":
            time.sleep(2)
            continue

        message = msg["message"].lower()

        if message.startswith("orders"):
            if len(orders) == 0:
                post_message(sc, "No active orders right now, wanna give me something to do? :raised_hands:", channel)
            else:
                post_message(sc, "Current orders:\n{0}".format(orders), channel)
            continue

        if message.startswith("track"):
            params = msg["message"].lower().split(" ")
            params.pop(0)
            if len(params) != 2:
                post_message(sc, "Wrong amount of paramaters.\nPlease format message as \"Tracking <provider> <tracking no>\"", channel)
                continue

            provider = params[0]
            tracking_no = params[1]
            if provider not in providers:
                post_message(sc, "The first parameter should be the tracking provider.\nThe following providers are supported \"{0}\"".format(", ".join(list(providers.keys()))), channel)
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
                post_message(sc, "This package is already being tracked\nThe last status was:\n{0}".format(latest_status), channel)
            else:
                orders[str(uuid.uuid4())] = {"tracking":{"provider": provider, "tracking_no": tracking_no, "url": get_url, "status": "", "last_updated": 0}}
                post_message(sc, "I'll start tracking this package and keep you updated on it. :package:", channel)
            continue

        if message.startswith("remove") or message.startswith("delete"):
            params = msg["message"].lower().split(" ")
            params.pop(0)
            if len(params) != 1:
                post_message(sc, "Wrong amount of paramaters.\nPlease format message as \"Remove|Delete <order_id>\"", channel)
                continue
            order_id = params[0]
            if order_id == "--all":
                orders = {}
                post_message(sc, "Removed all active orders :exclamation:", channel)
                continue
            if order_id not in orders:
                current_orders = "\n".join(list(orders.keys()))
                if len(orders) == 0:
                    post_message(sc, "No active orders right now, wanna give me something to do? :raised_hands:", channel)
                else:
                    post_message(sc, "Could not find order_id in orders, the following order_id are available:\n{0}".format(current_orders), channel)
                continue
            orders.pop(order_id)
            post_message(sc, "{0} succesfully removed from orders :exclamation:".format(order_id), channel)
            continue

        post_message(sc, "Not a valid order :question:", channel)

    time.sleep(2)
