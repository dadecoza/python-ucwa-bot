#!/usr/bin/python
import sys
import os
import vodaucwa
import suds
from suds.client import Client
from suds.sudsobject import Property
from suds.transport.https import HttpAuthenticated
import re

MIDTIER = "midtier.company.corp:8080"
AR_SERVER = "arserver.company.corp"
AR_USERNAME = "aruser"
AR_PASSWORD = "secret"
UC_URL = "https://lyncdiscoverinternal.company.com/"
UC_USERNAME = "company\\botuser"
UC_PASSWORD = "secret"


def messageReceived(message):
    m = re.search('(INC\d+)', message.message)
    if m:
        inc = m.group(1)
        message.reply(getIncidentDetails(inc))
    else:
        message.reply("expected incident number")


def connectRemedy(wsdl, username, password):
    remedy = None
    remedy = Client(wsdl, cache=None)
    auth = remedy.factory.create("AuthenticationInfo")
    auth.userName = username
    auth.password = password
    remedy.set_options(soapheaders=(auth))
    return remedy


def getIncidentDetails(inc):
    wsdl = "http://%s/arsys/WSDL/public/%s/HPD_IncidentInterface_WS" % (MIDTIER, AR_SERVER)
    remedy = connectRemedy(wsdl, AR_USERNAME, AR_PASSWORD)
    details = []
    if remedy:
        try:
            resp = remedy.service.HelpDesk_Query_Service(inc)
            for k, v in resp:
                if v is not None:
                    details.append("%s : %s " % (k, v))
        except suds.WebFault as err:
            details.append(str(err))
    else:
        return "failed to connect to Remedy"

    if not details:
        details.append("no data found")

    return "\n".join(details)


def main():
    bot = vodaucwa.LyncBot()
    bot.setMessageCallback(messageReceived)
#    proxy = "http://proxy.company.com:80/"
#    os.environ["http_proxy"] = proxy
#    os.environ["https_proxy"] = proxy
    bot.authenticate(UC_URL, UC_USERNAME, UC_PASSWORD)
    bot.loop()

if __name__ == '__main__':
    main()
