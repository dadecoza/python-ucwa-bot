from s4b_bot import SkypeForBusinessBot


username = "company\\username"
password = "secret"
url = "https://lyncdiscoverinternal.company.com/"


def message_callback(message):
    uri = message.uri
    text = message.message
    print("%s: %s" % (uri, text))
    message.reply("""hi %s!, you said "%s".""" % (uri, text))


def main():
    bot = SkypeForBusinessBot(url, username, password)
    bot.set_message_callback(message_callback)
    bot.loop()


if __name__ == '__main__':
    main()
