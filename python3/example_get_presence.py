from s4b_send import SkypeForBusinessSend

username = "company\\username"
password = "secret"
url = "https://lyncdiscoverinternal.company.com/"

s4b = SkypeForBusinessSend(url, username, password)

uri = "sip:person@company.com"

presence = s4b.get_presence(uri)

print(presence)
