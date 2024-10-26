import json

from resources.lib.rtve.rtve import rtve
import urllib.request, urllib.parse, urllib.error
#un munt de testos de les diferents funcions usades

rtve = rtve("", "")
(temporades, videos) = rtve.listProgrames("https://api.rtve.es/api/tematicas/823")
type(temporades[0])
print(len(temporades))
for temp in temporades:
    print(temp.url)
