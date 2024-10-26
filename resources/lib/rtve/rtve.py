from __future__ import division

import json
from builtins import object

from resources.lib.video.FolderVideo import FolderVideo
from resources.lib.utils.Utils import *
import xbmc

from resources.lib.video.Video import Video


class rtve(object):
    def __init__(self, addon_path, addon):
        xbmc.log("plugin.video.rtve classe rtve - init() ")
        self.addon_path = addon_path

    # mode = None
    def listHome(self):
        xbmc.log("plugin.video.rtve classe rtve - listHome() ")
        coleccions = FolderVideo('Television', "https://api.rtve.es/api/tematicas/823", "getProgrames", "",
                                 "")
        return [coleccions]


    def listProgrames(self, urlApi):
        xbmc.log("plugin.video.rtve - programas " + urlApi)
        folders = []
        videos = []
        print(urlApi)
        hijosJson ="hijos.json?page="
        videosJson = "videos.json?page="
        hijosUrl = ""
        if hijosJson in urlApi:
            hijosUrl = urlApi
        elif not videosJson in urlApi:
            hijosUrl = urlApi + "/" + hijosJson + "1"

        if hijosUrl:
            split = hijosUrl.split("=")
            currentPage = int(split[1])
            nextHijosUrl = split[0] + "=" + str(currentPage+1)
            previousHijosUrl = ""
            if currentPage>1:
                previousHijosUrl = split[0] + "=" + str(currentPage - 1)

        videosUrl = ""
        if videosJson in urlApi:
            videosUrl = urlApi
        elif not hijosJson in urlApi:
            videosUrl = urlApi + "/" + videosJson +"1"

        if videosUrl:
            split = videosUrl.split("=")
            currentPage = int(split[1])
            nextVideosUrl = split[0] + "=" + str(currentPage + 1)
            previousVideosUrl = ""
            if currentPage > 1:
                previousVideosUrl = split[0] + "=" + str(currentPage - 1)

        if hijosUrl:
            hijosItems = getJsonData(hijosUrl)['page']['items']
            if len(hijosItems)>0:

                for item in hijosItems:
                    xbmc.log("plugin.video.rtve - element " + str(item))
                    foldVideo = FolderVideo(item['title'], "https://api.rtve.es/api/tematicas/" + item['id'], 'getProgrames')
                    folders.append(foldVideo)

                if previousHijosUrl:
                    folders.append(FolderVideo("Anterior Pag", previousHijosUrl, 'getProgrames'))

                folders.append(FolderVideo("Siguiente Pag", nextHijosUrl, 'getProgrames'))
                return (folders, videos)

        if videosUrl:
            videosItems = getJsonData(videosUrl)['page']['items']
            if len(videosItems)>0:
                for item in videosItems:
                    xbmc.log("plugin.video.rtve - element " + str(item))
                    img = item['thumbnail']
                    video = Video(item['title'], img, img, item['description'],  item['id'], "")
                    videos.append(video)

                if previousVideosUrl:
                    folders.append(FolderVideo("Anterior Pag", previousVideosUrl, 'getProgrames'))

                folders.append(FolderVideo("Siguiente Pag", nextVideosUrl, 'getProgrames'))

        return (folders, videos)