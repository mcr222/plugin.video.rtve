import urllib.request, urllib.parse, urllib.error

def buildUrl(query, base_url):
    return base_url + '?' + urllib.parse.urlencode(query)
