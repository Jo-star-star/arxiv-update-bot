#!/usr/bin/python3
import argparse
import configparser
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import feedparser
import telebot
from datetime import datetime

date = datetime.now()
if date.strftime('%A') in ["Saturday", "Sunday"]:
    print("C'est le week-end!")
    exit(0);

DEFAULT_CONFIGURATION_PATH = "/home/jo/Config/aub.config.ini"


def load_config(path):
    """Load the configuration from the path.
    It will try to load the token from the [bot] section.
    Then it will iterate over the other sections to find the updates to verify.

    Args:
        path (string): path of the config file.

    Raises:
        Exception: if the bot section is not found.
        Exception: if there is no token value in the bot section.
        Exception: if an update section is not complete.

    Returns:
        (string, list): the token and the list of updates.
    """
    config = configparser.ConfigParser()
    config.read(path)

    if "bot" not in config:
        raise Exception(
            "A bot section must be in the configuration file to set the token"
        )

    bot_config = config["bot"]
    if "token" not in bot_config:
        raise Exception("The bot section must have the bot token.")

    token = bot_config["token"]
    updates = []
    for section in config.sections():
        if str(section) != "bot":
            current_section = config[section]
            if not (
                "category" in current_section
                and "chat_id" in current_section
                and "buzzwords" in current_section
            ):
                raise Exception(
                    f"The section {current_section} is not complete. Missing one of three : category, chat_id or buzzwords."
                )
            updates.append(
                {
                    "category": current_section["category"].split(","),
                    "chat_id": current_section["chat_id"],
                    "buzzwords": current_section["buzzwords"].split(","),
                    "authors": current_section["authors"].split(","),
                }
            )
    return token, updates

def flatten(l):
    return [item for sublist in l for item in sublist]

def get_articles(category, buzzwords):
    """Get the articles from arXiv.

    It get the RSS flux re;ated to the category of the update,
    then filter the entries with the buzzwords.

    Args:
        category (string): the name of the category.
        buzzwords (list): a list of buzzwords.

    Returns:
        list: list of entries.
    """
    news_feed = feedparser.parse(f"http://export.arxiv.org/rss/{category}")
    res = []
    #print(news_feed)
    for entry in news_feed.entries:
        #print(entry)
        for buzzword in buzzwords["article"]:
            #Test authors
            if  fuzz.partial_ratio(buzzword, entry.title) > 90 or fuzz.partial_ratio(buzzword, entry.summary ) > 90:
                if entry not in res:
                    res.append(entry)
        for author in buzzwords["authors"]:
            #print(author)
            if fuzz.partial_ratio(author, entry.authors) > 90:
                if entry not in res:
                    res.append(entry)
    return res


def send_articles(bot, chat_id, categories, buzzwords, quiet=False):
    """Send the articles to telegram.

    Args:
        bot (Telebot): telebot instance.
        chat_id (int): the chat id to send the message. Either a group or individual.
        category (string): the category for arXiv.
        buzzwords (list): list of buzzwords.
        quiet (bool, optional): whether to send a messae when no article is found. Defaults to False.
    """
    articles = [] 
    for category in categories:
        results = get_articles(category, buzzwords)
        for entry in results:
            if entry not in articles:
                articles.append(entry)
    print(articles)

    if not articles:
        if not quiet:
            bot.send_message(
                chat_id,
                text="I scraped the arXiv RSS but found nothing of interest for you. Sorry.",
            )
    else:
        bot.send_message(
            chat_id,
            text=f"You are going to be happy. I found {len(articles)} article(s) of potential interest.",
        )
        for article in articles:
            processed_summary = article.summary.replace("\n"," ").replace("<p>","").replace("</p>","")
            print(processed_summary)
            bot.send_message(
                chat_id,
                text=f"<strong>Title</strong>: {article.title}\n<strong>Authors</strong>: {article.authors[0]['name']}\n<strong>Link</strong>: {article.id}\n<strong>Abstract:</strong>\n{processed_summary}"
            )


def main():
    """
    The main function.
    """
    parser = argparse.ArgumentParser(description="Scrap the arXiv")
    parser.add_argument(
        "-c",
        "--config-path",
        help="Path for configuration path. Replace default of /etc/arxiv-update-bot/config.ini",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="If quiet is set, then the bot will not send message if no article are found.",
    )
    args = parser.parse_args()
    config_path = args.config_path or DEFAULT_CONFIGURATION_PATH
    print(f"Config path:{config_path}\n")
    quiet = args.quiet

    token, updates = load_config(config_path)
    print(token, updates) 

    
    bot = telebot.TeleBot(token, parse_mode="HTML")

    for update in updates:
        print(bot)
        buzzwords = {"authors": update["authors"], "article" : update["buzzwords"]}
        send_articles(
            bot, update["chat_id"], update["category"], buzzwords, quiet=quiet
        )


if __name__ == "__main__":
    main()
