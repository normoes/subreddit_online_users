#! /usr/bin/python3

"""

CLIENT_SECRET=$(pass show work/CSS/reddit/subreddit_user_count) CLIENT_ID=$(pass show work/CSS/reddit/subreddit_user_count_id) PASSWORD=$(pass show work/CSS/reddit/xmrto-community) USERNAME=$(pass show work/CSS/reddit/xmrto-community_user) python active_user_bot.py

python active_user_bot.py --secret <client_secret> --id <client_id> --password <reddit_password> --user <reddit_username>

"""

# Imports
import os
import praw
import time
import json
import datetime as dt
import logging
import argparse

from utils import database

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

DEBUG = False
MIN_RUNS = 1
MIN_INTERVAL = 1

CLIENT_SECRET = os.environ.get("CLIENT_SECRET", None)
CLIENT_ID = os.environ.get("CLIENT_ID", None)
USERNAME = os.environ.get("USERNAME", None)
PASSWORD = os.environ.get("PASSWORD", None)
RUNS = MIN_RUNS
INTERVAL = MIN_INTERVAL

# read securely stored environment variables set in AWS Lambda
# Use different variables locally
if "SERVERTYPE" in os.environ and os.environ["SERVERTYPE"] == "AWS Lambda":
    import boto3
    from base64 import b64decode

    ENCRYPTED = os.environ["DATABASE_URL"]
    # Decrypt code should run once and variables stored outside of the function
    # handler so that these are decrypted once per container
    DATABASE_URL = bytes.decode(
        boto3.client("kms").decrypt(CiphertextBlob=b64decode(ENCRYPTED))["Plaintext"]
    )
    CLIENT_SECRET = bytes.decode(
        boto3.client("kms").decrypt(CiphertextBlob=b64decode(CLIENT_SECRET))[
            "Plaintext"
        ]
    )
    CLIENT_ID = bytes.decode(
        boto3.client("kms").decrypt(CiphertextBlob=b64decode(CLIENT_ID))["Plaintext"]
    )
    PASSWORD = bytes.decode(
        boto3.client("kms").decrypt(CiphertextBlob=b64decode(PASSWORD))["Plaintext"]
    )
    USERNAME = bytes.decode(
        boto3.client("kms").decrypt(CiphertextBlob=b64decode(USERNAME))["Plaintext"]
    )
    DB_TYPE = database.POSTGRES
else:
    parser = argparse.ArgumentParser(
        description="Get number of subscribers and active user count of subreddit.",
        epilog="",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    group_auth = parser.add_argument_group("authentication")
    group_auth.add_argument("-s", "--secret", help="Reddit app's client secret.")
    group_auth.add_argument("-i", "--id", help="Reddit app's client id.")
    group_auth.add_argument("-p", "--password", help="Reddit password.")
    group_auth.add_argument("-u", "--user", help="Reddit username.")
    group = parser.add_argument_group("behaviour")

    group.add_argument(
        "--runs",
        default=MIN_RUNS,
        type=int,
        help="How often active users should be retreived. Used in combination with --interval. If set to <=1 it runs once.",
    )
    group.add_argument(
        "--interval",
        default=MIN_INTERVAL,
        type=int,
        help="Waiting period [seconds] between runs. Used in combination with --runs.",
    )
    args = parser.parse_args()

    if not CLIENT_SECRET:
        CLIENT_SECRET = args.secret

    if not CLIENT_ID:
        CLIENT_ID = args.id

    if not PASSWORD:
        PASSWORD = args.password

    if not USERNAME:
        USERNAME = args.user

    RUNS = args.runs
    INTERVAL = args.interval
    log.setLevel(logging.DEBUG)
    # DB_TYPE = database.POSTGRES
    # DATABASE_URL = "data.db"
    DB_TYPE = database.POSTGRES
    DATABASE_URL = "postgres@localhost:5432/test"


class OnlineUserBot:
    """A simple bot that finds the number of users online a specifc Subreddit."""

    def __init__(
        self,
        subreddit_name,
        interval,
        runs,
        client_id,
        client_secret,
        password,
        user_agent,
        username,
        debug=False,
    ):
        self.subreddit_name = subreddit_name
        self.interval = max(int(interval), MIN_INTERVAL)
        self.runs = max(int(runs), MIN_RUNS)
        self.client_id = client_id
        self.client_secret = client_secret
        self.password = password
        self.user_agent = user_agent
        self.username = username
        self.db = None
        self.debug = debug

    def auth(self):
        self.reddit = praw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            password=self.password,
            user_agent=self.user_agent,
            username=self.username,
        )

        self.subreddit = self.reddit.subreddit(self.subreddit_name)

    def get_users_online(self):
        return self.subreddit.accounts_active

    def get_subscribers(self):
        return self.subreddit.subscribers

    def get_public_description(self):
        return self.subreddit.public_description

    def save_to_db(self, subreddit):
        if self.db and not self.debug:
            self.db.insert_(database.SUBREDDITS, subreddit)

    def __check_users(self):
        self.auth()
        time_checked = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        users_online = self.get_users_online()
        subscribers = self.get_subscribers()

        subreddit = {
            "subreddit": self.subreddit_name,
            "subscribers": subscribers,
            "users_online": users_online,
            "created": time_checked,
        }

        self.save_to_db(subreddit=subreddit)

        log.info(json.dumps(subreddit))

    def run_bot(self):
        if self.runs <= MIN_RUNS:
            self.__check_users()
        elif self.runs > MIN_RUNS:
            for i in range(self.runs):
                self.__check_users()
                time.sleep(self.interval)


def check_online_users(event, context):
    subreddits = ("Monero",)
    for subreddit in subreddits:
        # Change the input to this class with your information from the Reddit API (See README.md for instructions)
        bot = OnlineUserBot(
            subreddit_name=subreddit,
            interval=INTERVAL,
            runs=RUNS,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            password=PASSWORD,
            user_agent="subreddit_user_count1.0",
            username=USERNAME,
            debug=DEBUG,
        )
        bot.db = database.Db(dbtype=DB_TYPE, dbname=DATABASE_URL)
        bot.run_bot()


if __name__ == "__main__":
    check_online_users(event=None, context=None)
