import json

from resources.lib.rtve.rtve import rtve
import urllib.request, urllib.parse, urllib.error
#un munt de testos de les diferents funcions usades

tv3 = rtve("", "")
#tv3.listColeccions()
(temporades, videos) = tv3.listProgrames("https://api.rtve.es/api/tematicas/823")
type(temporades[0])
# temporades = tv3.getListTemporades('200164279')
print(len(temporades))
for temp in temporades:
    print(temp.url)

#capitols = tv3.getListVideos("200164279_17a Temporada")
#print(len(capitols))
#for cap in capitols:
#    print(cap.title + " " + cap.title + " " + str(cap.iconImage))

#videos = tv3.getListVideos("https://www.RTVE.cat/RTVE/bricoheroes/capitols/temporada/2/")
#print(len(videos))
#print(videos[0])
#videoId = 6176980
#apiJsonUrl = "https://api-media.RTVE.cat/pvideo/media.jsp?media=video&versio=vast&idint={}&profile=pc_RTVE&format=dm".format( videoId)
#print(apiJsonUrl)
#with urllib.request.urlopen(apiJsonUrl) as response:
#    data = response.read()
#    json_data = json.loads(data)
#    print(json_data['media']['url'][0]['file'])
