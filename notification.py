"""
Plurk 新發噗通知

1. 每 10 分鐘檢查, 若 11 分鐘 (多加 1 分鐘避免誤差) 內有新發噗, 則通知
"""


import json
import re
from datetime import datetime, timedelta, timezone

import requests
from telegram import Bot, Update

TOKEN = "{telegram_token}"
MY_CHAT_ID = "{your_chat_id}"
BASE_URL = "https://www.plurk.com"
plurk_ids = (000000, )


def lambda_handler(event, context):
    bot = Bot(TOKEN)

    # EventBridge (CloudWatch Events)
    # 定期執行的排程
    if event.get("source") == "aws.events":
        print("Check from AWS EventBridge.")

        for i in plurk_ids:
            e_plurk = Plurk(i)

            if e_plurk.get_latest_plurk():
                print("Have new plurks!")
                for p in e_plurk.new_plurks:
                    send_message(bot, p)

        return

    # 判斷是 post 以及有 body 才往下走, 代表是從 telegram 發來的 webhook
    try:
        if event["requestContext"]["http"]["method"] != "POST" or not event.get("body"):
            return {"statusCode": 200, "body": json.dumps("Add layers!")}
    except KeyError:
        pass

    update = Update.de_json(json.loads(event.get("body")), bot)
    chat_id = update.message.chat.id
    text = update.message.text

    plurk = Plurk(plurk_ids[0])

    response_text = text
    if text == "/start":
        print("Started!")
        response_text = f"Started! Your id is {chat_id}."
        bot.sendMessage(chat_id=chat_id, text=response_text)
        return

    if text.startswith("/check"):
        if plurk.get_latest_plurk():
            send_message(bot, "\n".join(plurk.new_plurks))
        else:
            send_message(bot, "No new plurk!")

        return

    if text.startswith("/test"):
        print("Test I'm alive.")
        send_message(bot, "I'm alive.")
        return


class Plurk:
    def __init__(self, user_id):
        self.user_id = user_id
        # set offset to now for first time
        self.offset = format_time_to_offset(datetime.utcnow())
        self.new_plurks = []

    def get_plurks(self):
        """user_id,  plurk user id
        offset, get plurks before this time
        only_user = 1, get only this user's plurks, no replurk
        plurk only return 20 plurks once"""

        postdata = {"user_id": self.user_id, "offset": self.offset, "only_user": "1"}
        r = requests.post(
            f"{BASE_URL}/TimeLine/getPlurks",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.4985.0 Safari/537.36",
                "Referer": BASE_URL,
            },
            data=postdata,
        )
        json_result = r.json()

        if "error" in json_result:
            if json_result["error"] == "NoReadPermissionError":
                print("This is a private timeline.")
        elif "plurks" in json_result and not json_result["plurks"]:
            print("Get Plurks...End")
        else:
            return json_result

    def get_latest_plurk(self):
        """get latest plurk in 10 minutes"""
        response_json = self.get_plurks()
        plurks = response_json.get("plurks", [])
        have_new_plurk = False

        for plurk in plurks:
            posted_time_utc = parse_time(plurk["posted"])
            now_time_utc = datetime.utcnow()

            # 檢查 10 分鐘內是否有新發噗
            if posted_time_utc > now_time_utc - timedelta(minutes=11):
                have_new_plurk = True

                post_time = change_timezone_local(posted_time_utc)
                plurk_content = plurk["content_raw"].replace("\n", " ")

                self.new_plurks.append(f"{post_time} {plurk_content} #plurk")

        return have_new_plurk


def check_response(plurk_id):
    payload = {"plurk_id": plurk_id, "from_response_id": "0"}
    r = requests.post("https://www.plurk.com/Responses/get", data=payload)

    new_responses = []
    responses = r.json().get("responses", [])
    for res in responses:
        posted_time_utc = parse_time(res["posted"])
        now_time_utc = datetime.utcnow()

        if posted_time_utc > now_time_utc - timedelta(minutes=11):
            post_time = change_timezone_local(posted_time_utc)
            plurk_content = res["content_raw"].replace("\n", " ")

            new_responses.append(f"{post_time} {plurk_content} #plurk")

    return new_responses


def check_weibo():
    url = "https://m.weibo.cn/api/container/getIndex?containerid=1076033146760504"
    res = requests.get(url)
    data = res.json()

    messages = []
    cards = data.get("data", {}).get("cards", [])
    for card in cards:
        mblog = card.get("mblog", {})
        created_at = mblog.get("created_at")
        # created_time formate: Tue Jul 12 11:32:02 +0800 2022
        created_time = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
        created_time_utc = created_time.astimezone(timezone.utc)
        utc_now = datetime.utcnow().replace(tzinfo=timezone.utc)

        if created_time_utc > utc_now - timedelta(minutes=11):
            text = mblog.get("raw_text")
            if not text:
                text = mblog.get("text", "Empty")
                text = re.sub(r"\<.*?\>", "", text)

            messages.append(f"{created_time} {text} #weibo")

    messages.reverse()
    return messages


def parse_time(time: str) -> datetime:
    """parse original time from plurk
    e.g. 'Sat, 11 Jan 2020 01:14:29 GMT' string to datetime
    """
    return datetime.strptime(time, "%a, %d %b %Y %H:%M:%S %Z")


def format_time_to_offset(time: datetime) -> str:
    """change time to plurk offset format
    e.g. datetime to '2020-01-11T01:14:29.000Z' string
    """
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def change_timezone_local(time: datetime) -> str:
    """change datetime to local time string (UTC+8)"""
    local_time = time.replace(tzinfo=timezone.utc).astimezone(
        tz=timezone(timedelta(hours=8))
    )
    return local_time.strftime("%Y-%m-%d %H:%M:%S")


def send_message(bot, text):
    """回傳訊息"""
    bot.sendMessage(chat_id=MY_CHAT_ID, text=text)


if __name__ == "__main__":
    plurk = Plurk()
    plurk.get_latest_plurk()
    print("\n".join(plurk.new_plurks))
