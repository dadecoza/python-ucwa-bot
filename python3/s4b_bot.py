import requests
import re
import json
import uuid
import logging
import random
import _thread
import time
import urllib


class Message:
    def __init__(self, url, uri, message, authorization, typing_url, proxy):
        self.url = url
        self.uri = uri
        self.message = message
        self.authorization = authorization
        self.typing_url = typing_url
        self.proxy = proxy
        _thread.start_new_thread(self.typing, ())
        self.replied = False

    def read(self):
        return message

    def sender(self):
        return uri

    def typing(self):
        while not self.replied:
            r = requests.post(
                self.typing_url,
                headers={"Authorization": self.authorization},
                proxies=self.proxy
            )
            time.sleep(8)

    def reply(self, text):
        headers = {
            "Content-Type": "text/plain",
            "Authorization": self.authorization
        }
        r = requests.post(self.url, data=text, headers=headers, proxies=self.proxy)
        self.replied = True


class SkypeForBusinessBot():
    proxy = None
    url_root = None
    url_user = None
    url_oath = None
    url_application = None
    url_messaging = None
    url_events = None
    url_reportmyactivity = None
    url_makemeavailable = None
    auth_header = None
    operation_id = None
    session_context = None
    message_callback = None
    username = None
    password = None

    def fix_url(self, url):
        return re.sub(r'^(https?://.*?)/', self.url_root, url)

    def set_root_url(self, discovery_url):
        j = self.get(discovery_url)
        url = j['_links']['self']['href']
        m = re.search(r'^(https?://.*?/)', url)
        root_url = m.group(1)
        logging.debug("root url: %s" % root_url)
        self.url_root = root_url

    def set_user_url(self, discovery_url):
        j = self.get(discovery_url)
        url = j['_links']['user']['href']
        url = self.fix_url(url)
        logging.debug("user url: %s" % url)
        self.url_user = url

    def set_oauth_url(self):
        r = requests.get(self.url_user, proxies=self.proxy)
        m = re.search('MsRtcOAuth href="(.*?)"', str(r.headers))
        url = m.group(1)
        url = self.fix_url(url)
        logging.debug("oauth url: %s" % url)
        self.url_oauth = url

    def set_auth_header(self):
        data = {
            'grant_type': 'password',
            'username': self.username,
            'password': self.password
        }
        r = requests.post(
            self.url_oauth,
            data=data,
            headers={
                "Content-Type":
                    "application/x-www-form-urlencoded;charset=UTF-8"
            },
            proxies=self.proxy
        )
        j = r.json()
        auth_header = "%s %s" % (j['token_type'], j['access_token'])
        logging.debug("auth header: %s" % auth_header)
        self.auth_header = auth_header

    def set_application_url(self):
        j = self.get(self.url_user)
        url = j['_links']['applications']['href']
        url = self.fix_url(url)
        logging.debug("application url: %s" % url)
        self.url_application = url

    def setup_application(self):
        endpointid = "%032x" % random.getrandbits(128)
        data = {
            "UserAgent": "Python Client",
            "EndpointId": endpointid,
            "Culture": "en-US",
        }
        j = self.post(self.url_application, data)
        self.url_messaging = self.url_root+j['_embedded']['communication']['_links']['startMessaging']['href']
        self.url_events = self.url_root+j['_links']['events']['href']
        self_application_url = self.url_root+j['_links']['self']['href']
        self.url_reportmyactivity = self_application_url+"/reportMyActivity"
        self.url_makemeavailable = self.url_root+j['_embedded']['me']['_links']['makeMeAvailable']['href']
        return

    def make_me_available(self):
        data = {
            "SupportedModalities": ["Messaging"]
        }
        self.post(self.url_makemeavailable, data)

    def accept_chat(self, accept_url):
        self.post(accept_url)

    def get_participant_uri(self, participant_url):
        j = self.get(participant_url)
        return j['uri']

    def set_message_callback(self, func):
        self.message_callback = func

    def report_my_activity(self):
        reportmyactivity_url = self.url_reportmyactivity
        if reportmyactivity_url is not None:
            self.post(reportmyactivity_url)

    def process_events(self):
        j = self.get(self.url_events, params={"timeout": "180"})

        self.url_events = self.url_root+j['_links']['next']['href']
        for sender in j['sender']:
            if sender['rel'] == "communication":
                for event in sender['events']:
                    if '_embedded' in event:
                        for action in event['_embedded']:
                            if action == 'messagingInvitation':
                                if event['_embedded'][action]['direction'] == "Incoming":
                                    if 'accept' in event['_embedded']['messagingInvitation']['_links']:
                                        accept_url = self.url_root+event['_embedded']['messagingInvitation']['_links']['accept']['href']
                                        self.accept_chat(accept_url)
            elif sender['rel'] == "conversation":
                for event in sender['events']:
                    if event['link']['rel'] == 'message':
                        if 'plainMessage' in event['_embedded']['message']['_links']:
                            if (self.message_callback is not None):
                                participant_url = self.url_root+event['_embedded']['message']['_links']['participant']['href']
                                uri = self.get_participant_uri(participant_url)
                                raw = event['_embedded']['message']['_links']['plainMessage']['href']
                                message_url = self.url_root+event['_embedded']['message']['_links']['self']['href']
                                logging.debug("messaging url: " + message_url)
                                m = re.search(r'^\S+?,(.*)', raw)
                                message = ""
                                if m:
                                    message = urllib.parse.unquote(m.group(1).replace("+", " "))
                                messaging_url = self.url_root+event['_embedded']['message']['_links']['messaging']['href']
                                istyping_url = messaging_url+"/typing"
                                _thread.start_new_thread(
                                    self.message_callback, (
                                        Message(
                                            message_url,
                                            uri,
                                            message,
                                            self.auth_header,
                                            istyping_url,
                                            self.proxy
                                        ),
                                    )
                                )

    def heartbeat(self):
        while True:
            self.report_my_activity()
            time.sleep(60)

    def get(self, url, params=None):
        headers = {"Content-Type": "application/json"}

        if self.auth_header:
            headers["Authorization"] = self.auth_header

        r = requests.get(
            url,
            headers=headers,
            proxies=self.proxy,
            params=params
        )

        if r.status_code == 401:
            self.set_auth_header()
            return self.get(url, params)
        elif r.status_code == 404:
            self.set_auth_header()
            self.set_application_url()
            return self.get(url, params)

        if not r.text:
            return {}

        try:
            j = r.json()
            return j
        except ValueError as e:
            print(r.text)
            pass

        return {}

    def post(self, url, data=None, params=None):
        headers = {"Content-Type": "application/json"}

        if self.auth_header:
            headers["Authorization"] = self.auth_header

        r = requests.post(
            url,
            headers=headers,
            proxies=self.proxy,
            json=data
        )

        if r.status_code == 401:
            self.set_auth_header()
            return self.post(url, data)
        elif r.status_code == 404:
            self.set_auth_header()
            self.set_application_url()
            return self.post(url, data)

        if not r.text:
            return {}

        try:
            j = r.json()
            return j
        except ValueError as e:
            print(r.text)
            pass

        return {}

    def __init__(self, discovery_url, username, password, proxy=None):
        if proxy:
            self.proxy = {"http": proxy, "https": proxy}
        self.username = username
        self.password = password
        self.set_root_url(discovery_url)
        self.set_user_url(discovery_url)
        self.set_oauth_url()
        self.set_auth_header()
        self.set_application_url()
        self.operation_id = "%032x" % random.getrandbits(128)
        self.session_context = "%032x" % random.getrandbits(128)
        self.setup_application()
        self.make_me_available()
        _thread.start_new_thread(self.heartbeat, ())

    def loop(self):
        while True:
            self.process_events()
