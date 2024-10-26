import urllib.request, urllib.parse, urllib.error
import json

def buildUrl(query, base_url):
    return base_url + '?' + urllib.parse.urlencode(query)

def getJsonData(apiUrl):
    print(apiUrl)
    with urllib.request.urlopen(apiUrl) as response:
        data = response.read()
        json_data = json.loads(data)
        return json_data
