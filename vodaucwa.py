#!/usr/bin/env python
#
# A library to create a simple Skype for Business response bot using UCWA.
# Johannes le Roux <dade@dade.co.za>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser Public License for more details.

"""A library to create a simple Skype for Business response bot using UCWA"""

import urllib
import urllib2
import json
import re
import random
import thread
import time


class Message:
    def __init__(self, url, uri, message, authorization):
        self.url = url
        self.uri = uri
        self.message = message
        self.authorization = authorization

    def read(self):
        return message

    def sender(self):
        return uri

    def reply(self, text):
        for x in range(0, 5):
            try:
                message_req = urllib2.Request(url=self.url, data=text)
                message_req.add_header("Authorization", self.authorization)
                message_req.add_header('Content-Type', 'text/plain')
                urllib2.urlopen(message_req).read()
                break
            except:
                None
            time.sleep(3)


class LyncBot:
    def __init__(self):
        self.user_url = None
        self.application_url = None
        self.self_application_url = None
        self.authorization = None
        self.root_url = None
        self.messaging_url = None
        self.events_url = None
        self.operation_id = "%032x" % random.getrandbits(128)
        self.session_context = "%032x" % random.getrandbits(128)
        self.makemeavailable_url = None
        self.me_url = None
        self.photo_url = None
        self.presence_url = None
        self.messagecallback = None
        self.username = None
        self.password = None
        self.discover_url = None
        self.outgoing_message = None
        thread.start_new_thread(self.heartbeat, ())

    def authenticate(self, discover_url, username, password):
        try:
            req = urllib2.Request(discover_url)
            self.user_url = json.loads(urllib2.urlopen(req).read())['_links']['user']['href']
        except:
            print "Invalid Discover URL"
            raise

        self.discover_url = discover_url
        self.username = username
        self.password = password

        self.setAuthorization()
        self.setupApplication()
        self.makeMeAvailable()

    def setAuthorization(self):
        oauth_url = None
        req = urllib2.Request(self.user_url)
        try:
            urllib2.urlopen(req)
        except urllib2.HTTPError, e:
            m = re.search('WWW-Authenticate: MsRtcOAuth href="(.*?)"', str(e.headers))
            oauth_url = m.group(1)
        data = urllib.urlencode({
            'grant_type': 'password',
            'username': self.username,
            'password': self.password
        })

        try:
            req = urllib2.Request(url=oauth_url, data=data)
            req.add_header("Content-Type", 'application/x-www-form-urlencoded;charset=UTF-8')
            j = json.loads(urllib2.urlopen(req).read())
            token = j['access_token']
            type = j['token_type']
            self.authorization = "%s %s" % (type, token)
        except urllib2.HTTPError, e:
            print e.read()
            raise

    def setupApplication(self):
        self.application_url = self.http(self.user_url, None)['_links']['applications']['href']
        endpointid = "%032x" % random.getrandbits(128)
        data = json.dumps({
            "UserAgent": "UCWA Python",
            "EndpointId": endpointid,
            "Culture": "en-US",
        })
        m = re.search('^(https://.*?)/', self.application_url)
        self.root_url = m.group(1)
        j = self.http(self.application_url, data)
        self.messaging_url = self.root_url+j['_embedded']['communication']['_links']['startMessaging']['href']
        self.events_url = self.root_url+j['_links']['events']['href']
        self.self_application_url = self.root_url+j['_links']['self']['href']
        self.reportmyactivity_url = self.self_application_url+"/reportMyActivity"
        self.makemeavailable_url = self.root_url+j['_embedded']['me']['_links']['makeMeAvailable']['href']
        self.me_url = self.root_url+j['_embedded']['me']['_links']['self']['href']
        self.photo_url = self.root_url+j['_embedded']['me']['_links']['photo']['href']

    def processEvent(self):
        j = self.http(self.events_url+"&timeout=180", None)
        self.events_url = self.root_url+j['_links']['next']['href']
        for sender in j['sender']:
            if sender['rel'] == "communication":
                for event in sender['events']:
                    if '_embedded' in event:
                        for action in event['_embedded']:
                            if action == 'messagingInvitation':
                                if event['_embedded'][action]['direction'] == "Incoming":
                                    if 'accept' in event['_embedded']['messagingInvitation']['_links']:
                                        accept_url = self.root_url+event['_embedded']['messagingInvitation']['_links']['accept']['href']
                                        self.http(accept_url, "")
                                if event['_embedded'][action]['direction'] == "Outgoing":
                                    if event['_embedded'][action]['state'] == "Connected":
                                        if self.outgoing_message:
                                            messaging_url = self.root_url+event['_embedded'][action]['_links']['messaging']['href']
                                            message_req = urllib2.Request(url=messaging_url+'/messages', data=self.outgoing_message)
                                            message_req.add_header("Authorization", self.authorization)
                                            message_req.add_header('Content-Type', 'text/plain')
                                            urllib2.urlopen(message_req).read()
                                            self.outgoing_message = None
                                            self.http(messaging_url+'/terminate', '')
                                    elif event['_embedded'][action]['state'] != "Connecting":
                                        self.outgoing_message = None
            elif sender['rel'] == "conversation":
                for event in sender['events']:
                    if event['link']['rel'] == 'message':
                        if 'plainMessage' in event['_embedded']['message']['_links']:
                            if (self.messageCallback is not None):
                                participant_url = self.root_url+event['_embedded']['message']['_links']['participant']['href']
                                uri = self.http(participant_url, None)['uri']
                                raw = event['_embedded']['message']['_links']['plainMessage']['href']
                                message_url = self.root_url+event['_embedded']['message']['_links']['self']['href']
                                message = urllib.unquote(re.sub('\+', ' ', re.sub('^.*?,', '', raw))).rstrip()
                                try:
                                    thread.start_new_thread(self.messageCallback, (Message(message_url, uri, message, self.authorization),))
                                except Exception, e:
                                    print e

    def heartbeat(self):
        while 1:
            try:
                time.sleep(60)
                self.reportMyActivity()
            except:
                None

    def sendMessage(self, to, msg):
        if self.messaging_url:
            data = json.dumps({
                "importance": "Normal",
                "subject": "Notification",
                "telemetryId": None,
                "to": to,
                "sessionContext": "%032x" % random.getrandbits(128),
                "operationId": self.operation_id
            })
            self.http(self.messaging_url, data)
            self.outgoing_message = msg

    def makeMeAvailable(self):
        self.http(self.makemeavailable_url, '{"SupportedModalities":["Messaging"]}')

    def makeOnline(self):
        if presence_url is not None:
            self.http(presence_url, '{"availability" : "Online"}')

    def resetPresence(self):
        if presence_url is not None:
            self.http(presence_url, None)

    def reportMyActivity(self):
        reportmyactivity_url = self.reportmyactivity_url
        if reportmyactivity_url is not None:
            self.http(reportmyactivity_url, "")

    def setMessageCallback(self, func):
        self.messageCallback = func

    def loop(self):
        while(True):
            try:
                self.processEvent()
            except Exception, e:
                print e

    def http(self, url, data):
        content = None
        ret = None
        for x in range(0, 5):
            try:
                req = urllib2.Request(url=url, data=data)
                req.add_header("Authorization", self.authorization)
                req.add_header('Content-Type', 'application/json')
                content = urllib2.urlopen(req, timeout=300).read()
                break
            except urllib2.HTTPError, e:
                if e.code == 401:
                    self.setAuthorization()
                elif e.code == 404:
                    self.setAuthorization()
                    self.setupApplication()
                    self.makeMeAvailable()
                else:
                    print e.read()
            except Exception, e:
                print e
            if (x == 4):
                raise
            else:
                time.sleep(3)
        try:
            ret = json.loads(content)
        except ValueError, e:
            ret = content
        return ret
