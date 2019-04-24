from s4b_send import SkypeForBusinessSend

username = "company\\username"
password = "secret"
url = "https://lyncdiscoverinternal.company.com/"

s4b = SkypeForBusinessSend(url, username, password)

uri = "sip:person@company.com"
message = "hello world"
s4b.send_message(uri, message)
