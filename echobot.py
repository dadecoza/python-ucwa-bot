#!/usr/bin/python
import os
import vodaucwa


def messageReceived(message):
    message.reply("hi %s, you said \"%s\"." % (message.uri, message.message))


def main():
    bot = vodaucwa.LyncBot()
    bot.setMessageCallback(messageReceived)
    username = "domain\\username"
    password = "secret"
#    proxy = "http://proxy.company.com:80/"
#    os.environ["http_proxy"] = proxy
#    os.environ["https_proxy"] = proxy
    bot.authenticate("https://lyncdiscoverinternal.company.com/", username, password)
    bot.loop()

if __name__ == '__main__':
    main()
