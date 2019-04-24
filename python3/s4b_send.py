import requests
import re
import json
import logging
import random
import urllib
import _thread


class SkypeForBusinessSend():
    proxy = None
    url_root = None
    url_user = None
    url_oath = None
    url_application = None
    url_messaging = None
    url_events = None
    url_reportmyactivity = None
    url_makemeavailable = None
    url_search = None
    url_send = None
    url_stop = None
    auth_header = None
    operation_id = None
    session_context = None
    message_callback = None

    def fix_url(self, url):
        return re.sub(r'^(https?://.*?)/', self.url_root, url)

    def set_root_url(self, discovery_url):
        headers = {"Content-Type": "application/json"}
        r = requests.get(
            discovery_url,
            headers=headers,
            proxies=self.proxy
        )
        j = r.json()
        url = j['_links']['self']['href']
        m = re.search(r'^(https?://.*?/)', url)
        root_url = m.group(1)
        logging.debug("root url: %s" % root_url)
        self.url_root = root_url

    def set_user_url(self, discovery_url):
        headers = {"Content-Type": "application/json"}
        r = requests.get(
            discovery_url,
            headers=headers,
            proxies=self.proxy
        )
        j = r.json()
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

    def set_auth_header(self, username, password):
        data = {
            'grant_type': 'password',
            'username': username,
            'password': password
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
        headers = {
            "Content-Type": "application/json",
            "Authorization": self.auth_header
        }
        r = requests.get(
            self.url_user,
            headers=headers,
            proxies=self.proxy
        )
        j = r.json()
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
        r = requests.post(
            self.url_application,
            json=data,
            headers={"Authorization": self.auth_header},
            proxies=self.proxy
        )
        j = r.json()
        self.url_messaging = self.url_root+j['_embedded']['communication']['_links']['startMessaging']['href']
        self.url_events = self.url_root+j['_links']['events']['href']
        self_application_url = self.url_root+j['_links']['self']['href']
        self.url_reportmyactivity = self_application_url+"/reportMyActivity"
        self.url_makemeavailable = self.url_root+j['_embedded']['me']['_links']['makeMeAvailable']['href']
        self.url_search = self.url_root+j["_embedded"]["people"]["_links"]["search"]["href"]
        return

    def make_me_available(self):
        data = {
            "SupportedModalities": ["Messaging"]
        }
        r = requests.post(
            self.url_makemeavailable,
            json=data,
            headers={"Authorization": self.auth_header},
            proxies=self.proxy
        )

    def accept_chat(self, accept_url):
        r = requests.post(
            accept_url,
            headers={"Authorization": self.auth_header},
            proxies=self.proxy
        )

    def get_participant_uri(self, participant_url):
        r = requests.get(
            participant_url,
            headers={"Authorization": self.auth_header},
            proxies=self.proxy
        )
        j = r.json()
        return j['uri']

    def get_presence(self, uri):
        r = requests.get(
            self.url_search+"?query=%s" % (uri),
            headers={"Authorization": self.auth_header}
        )
        j = r.json()
        presence_url = self.url_root+j["_embedded"]["contact"][0]["_links"]["contactPresence"]["href"]
        r = requests.get(
            presence_url,
            headers={"Authorization": self.auth_header}
        )
        j = r.json()
        if "availability" in j:
            return j["availability"]
        return none

    def get_send_mesage_url(self):
        for t in range(0, 100):
            r = requests.get(
                self.url_events,
                headers={"Authorization": self.auth_header}
            )
            j = r.json()

            self.url_events = self.url_root+j['_links']['next']['href']

            for sender in j["sender"]:
                for event in sender["events"]:
                    if "_embedded" in event:
                        if "messagingInvitation" in event["_embedded"]:
                            operation_id = event["_embedded"]["messagingInvitation"]["operationId"]
                            state = event["_embedded"]["messagingInvitation"]["state"]
                            if state == "Failed" or operation_id != self.operation_id:
                                continue
                        if "messaging" in event["_embedded"]:
                            state = event["_embedded"]["messaging"]["state"]
                            if state == "Connected":
                                self.url_send = self.url_root+event["_embedded"]["messaging"]["_links"]["sendMessage"]["href"]
                                self.url_stop = self.url_root+event["_embedded"]["messaging"]["_links"]["stopMessaging"]["href"]
                                return
        if not self.url_send:
            raise ValueError('failed to find send url')

    def request_to_chat(self, uri):
        self.operation_id = "%032x" % random.getrandbits(128)
        data = {
            "importance": "Normal",
            "sessionContext": self.session_context,
            "subject": "",
            "telemetryId": None,
            "to": uri,
            "operationId": self.operation_id
        }
        r = requests.post(self.url_messaging, json=data, headers={"Authorization": self.auth_header})

    def send_the_message(self, message):
        requests.post(
            url=self.url_send,
            data=message,
            headers={"Content-Type": "text/plain", "Authorization": self.auth_header}
        )
        r = requests.get(
            self.url_events,
            headers={"Authorization": self.auth_header}
        )
        j = r.json()
        self.url_events = self.url_root+j['_links']['next']['href']

    def stop_message(self):
        requests.post(self.url_stop, headers={"Authorization": self.auth_header})
        requests.get(self.url_events, headers={"Authorization": self.auth_header})

    def send_message_thread(self, uri, message):
        try:
            self.request_to_chat(uri)
            self.get_send_mesage_url()
            self.send_the_message(message)
            self.stop_message()
        except Exception as e:
            print(str(e))

    def send_message(self, uri, message):
        #  _thread.start_new_thread(self.send_message_thread, (uri, message))
        self.send_message_thread(uri, message)

    def __init__(self, discovery_url, username, password, proxy=None):
        if proxy:
            self.proxy = {"http": proxy, "https": proxy}
        self.set_root_url(discovery_url)
        self.set_user_url(discovery_url)
        self.set_oauth_url()
        self.set_auth_header(username, password)
        self.set_application_url()
        self.session_context = "%032x" % random.getrandbits(128)
        self.setup_application()
