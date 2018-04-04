from slackclient import SlackClient
import time
import uuid
import requests
import json


def post_message(sc, message, channel):
    sc.api_call('chat.postMessage', channel=channel,
                text=message, username='SkyNet Alpha',
                icon_emoji=':robot_face:')

def get_channels(sc):
    channels = {}
    data = sc.api_call("channels.list")
    for item in data["channels"]:
        channels[item["name"]] = item["id"]
    return channels

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
                return_data.append(f'{item["date"]} {item["time"]} - {item["evtDscr"]}')
            return(return_data, delivered)

        if provider == "postnord":
            delivered = False
            return_data = []
            r = requests.get(url)
            data = r.json()["response"]["trackingInformationResponse"]["shipments"][0]["items"][0]["events"]
            delivered = (r.json()["response"]["trackingInformationResponse"]["shipments"][0]["status"].lower() == "delivered")
            for item in data:
                return_data.append(f'{item["eventTime"].replace("T", " ")} - {item["eventDescription"]}')
            return(return_data, delivered)
    except Exception:
        return(None, False)


with open('settings.json', 'r') as f:
    settings = json.load(f)

token = settings["token"]
sc = SlackClient(token)

providers = {"postnord": "https://www.postnord.dk/api/shipment/", "gls": "https://gls-group.eu/app/service/open/rest/EU/en/rstt001?match="}

try:
    with open('orders.json', 'r') as f:
        orders = json.load(f)
except FileNotFoundError:
    orders = {}

keys_to_delete = []
channels = get_channels(sc)
channel = channels["bot"]


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
    with open('orders.json', 'w') as f:
        json.dump(orders, f)

    latest_message = get_latest_message(sc, channel)

    for key, value in orders.items():
        for k, v in value.items():
            if k == "tracking":
                package_status, package_delivered = get_package(v["provider"], v["url"])
                if package_status is None:
                    continue
                if package_status[0] != v["status"]:
                    v["status"] = package_status[0]
                    post_message(sc, package_status[0], channel)
                if package_delivered:
                    post_message(sc, "This package has been delivered to you. I'll no longer track this package.", channel)
                    keys_to_delete.append(key)

    for key in keys_to_delete:
        orders.pop(key)

    keys_to_delete = []

    if latest_message["user"] == "SkyNet Alpha":
        time.sleep(2)
        continue

    if latest_message["message"].lower().startswith("orders"):
        post_message(sc, f"Current orders:\n{orders}", channel)
        continue

    if latest_message["message"].lower().startswith("track"):
        params = latest_message["message"].lower().split(" ")
        params.pop(0)
        if len(params) != 2:
            post_message(sc, "Wrong amount of paramaters.\nPlease format message as\"Tracking <provider> <tracking no>\"", channel)
            continue

        provider = params[0]
        tracking_no = params[1]
        if provider not in providers:
            post_message(sc, f"The first parameter should be the tracking provider.\nThe following providers are supported \"{', '.join(list(providers.keys()))}\"", channel)
            continue

        get_url = providers[provider] + tracking_no
        already_tracking = False

        for key, value in orders.items():
            for k, v in value.items():
                if k == "tracking":
                    already_tracking = (v["url"] == get_url)

        if already_tracking:
            post_message(sc, "This package is already being tracked", channel)
        else:
            orders[str(uuid.uuid4())] = {"tracking":{"provider": provider, "url": get_url, "status": ""}}
            post_message(sc, "I'll start tracking this package and keep you updated on in", channel)
        continue


    post_message(sc, "Not a valid order", channel)
    time.sleep(2)
