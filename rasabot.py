#!/usr/bin/python
import os
import requests
import vodaucwa


def messageReceived(message):
    uri = message.uri
    text = message.message.encode('utf-8')
    try:
        session = requests.Session()
        session.trust_env = False
        r = session.post("%s/webhooks/rest/webhook" % os.environ['bot_core_endpoint'], json={
            "sender": uri,
            "message": text
        })
        print r.text
        j = r.json()
        out = []
        for msg in j:
            if "text" in msg:
                out.append(msg["text"])
        mout = "\n".join(out)
        message.reply(mout.encode('utf-8'))
    except Exception, e:
        message.reply("Oops. Something went wrong. Please try again later. (%s)" % str(e))
        print e


def main():
    bot = vodaucwa.LyncBot()
    bot.setMessageCallback(messageReceived)
    username = os.environ['bot_skype_username']
    password = os.environ['bot_skype_password']
    discoveryurl = os.environ['bot_skype_discovery_url']
    bot.authenticate(discoveryurl, username, password)
    bot.loop()


if __name__ == '__main__':
    main()
