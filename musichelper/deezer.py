import json
import os
from typing import Literal
import httpx
from musichelper.exceptions import APIRequestError, LoginError, ServiceUnavailable
from musichelper.util import Parameters, SingletonMeta, clean_query, setup_logger
from asyncio import AbstractEventLoop
from logging import Logger, DEBUG, INFO
from deezer_asy import DeezerAsy
from datetime import datetime, timedelta
from .constants import *
import requests


class Deezer(metaclass=SingletonMeta):
    def __init__(self) -> None:
        parameters = Parameters().get_instance()
        self.__arl: str = parameters.deezer_arl
        self.__use_cache = parameters.deezer_cache
        self.__loop: AbstractEventLoop = parameters.loop
        self.is_debug: bool = parameters.debug

        self.token: str = None
        self.user: dict = None
        self.cookies: dict = {'arl': self.__arl}

        self.logger: Logger = setup_logger(
            "musichelper.deezer", level=DEBUG if self.is_debug else INFO)
        
        if self.__use_cache is True:
            self.try_use_cache()
        else:
            self.debug('Attempting to initialize a user using Deezer ARL...')
            self.initialize()

        self.debug("Deezer initialized")

    @property
    def initialized(self) -> bool:
        return self.token is not None and self.user is not None

    def try_save_cache(self):
        """
        Attempts to save the current state of the Deezer instance to a cache file.

        The cache file is named ".deezerdcache" and is saved in the current working directory.
        The cache file contains the following data:
            - cookies: The current cookies of the Deezer instance.
            - arl: The current ARL (Authentication Request Language) of the Deezer instance.
            - user: The current user data of the Deezer instance.
            - token: The current API token of the Deezer instance.
            - created_at: The ISO 8601 formatted date and time when the cache was created.

        This method does not return any value.

        Raises:
            IOError: If there is an error while writing to the cache file.
        """
        

        cache_file = ".deezerdcache"
        with open(cache_file, "w") as f:
            json.dump({
                "cookies": self.cookies,
                "arl": self.__arl,
                "user": self.user,
                "token": self.token,
                "created_at": datetime.now().isoformat()
            }, f)
            self.debug("Cache saved")

    def try_use_cache(self):
        """
        Tries to load authorization data from the cache file.

        If the cache file exists and the data is not expired (10 days),
        it loads the cookies, token, and user data from the cache file.

        Returns:
        ----------
            bool: True if the cache data is loaded successfully and not expired, False otherwise.
        """
        
        cache_file = ".deezerdcache"
        if os.path.exists(cache_file):
            try:
                self.debug("Attempting to load authorization data from the cache")
                with open(cache_file, "r") as f:
                    data:dict = json.load(f)
                    created_at:datetime = datetime.fromisoformat(data['created_at'])
                    if data and timedelta(days=10) > (datetime.now() - created_at):
                        self.cookies = data['cookies']
                        self.token = data['token']
                        self.user = data['user']
                        self.debug("Authorization data was downloaded from the cache")
                        return True
                    else:
                        os.remove(cache_file)
                        self.debug("The cache is out of date, it's 10 days old. Let's update it!")
                        return False
                    
            except Exception as e:
                os.remove(cache_file)
                self.logger.error("Cache loading error: %s", str(e))
                return False

    def initialize(self):
        token = self.token if self.token else 'null'
        method = api_methods.GET_USER_DATA
        data = None
        response = requests.post(api_urls.API_URL, headers=networking_settings.HTTP_HEADERS, params={
            "api_version": "1.0",
            "api_token": token,
            "input": "3",
            "method": method
        }, cookies=self.get_cookies())
        if response.status_code != 200:
            raise APIRequestError(str(response.status_code))

        data = response.json()
        self.cookies.update(response.cookies.copy())

        if "error" in data and data["error"]:
            error_type = list(data["error"].keys())[0]
            error_message = data["error"][error_type]

            raise APIRequestError(
                "{0} : {1}".format(error_type, error_message))

        data = data['results']
        self.token = data["checkForm"]

        if not data["USER"]["USER_ID"]:
            raise LoginError("Arl is invalid.")

        raw_user = data["USER"]

        if raw_user["USER_PICTURE"]:
            self.user = {
                "id": raw_user["USER_ID"],
                "name": raw_user["BLOG_NAME"],
                "arl": self.cookies["arl"],
                "image": f"https://e-cdns-images.dzcdn.net/images/user/{raw_user['USER_PICTURE']}/250x250-000000-80-0-0.jpg"
            }
        else:
            self.user = {
                "id": raw_user["USER_ID"],
                "name": raw_user["BLOG_NAME"],
                "arl": self.cookies["arl"],
                "image": "https://e-cdns-images.dzcdn.net/images/user/250x250-000000-80-0-0.jpg"
            }

        self.try_save_cache()
        return self.user

    def debug(self, msg: str, *args: object):
        if self.is_debug:
            self.logger.debug(msg, *args)

    def get_cookies(self) -> dict:
        """
        Get cookies in the domain of Deezer API.

        Returns:
        ----------
            dict: A dictionary containing the cookies. If cookies are already set, they are returned.
                Otherwise, a dictionary with 'arl' cookie is returned.
        """
        if self.cookies:
            return self.cookies

        return {'arl': self.__arl}

    async def _api_call(self, method: str, params: dict = {}) -> dict:
        """
        Makes an asynchronous API call to the Deezer API.

        Parameters:
        ----------
            method (str): The API method to call.
            params (dict, optional): Additional parameters to pass to the API call. Defaults to an empty dictionary.

        Returns:
        ----------
            dict: The JSON response from the API call.

        Raises:
        ----------
            APIRequestError: If the API call fails or returns an error.
        """
        token = self.token if self.token else 'null'
        if method != api_methods.GET_USER_DATA:
            token = self.token

        data = None
        async with httpx.AsyncClient(http2=True,
                                     headers=networking_settings.HTTP_HEADERS, params={
                "api_version": "1.0",
                "api_token": token,
                "input": "3",
                "method": method
                                     }, cookies=self.get_cookies()) as client:
            response = await client.post(api_urls.API_URL, json=params)
            if response.status_code != 200:
                raise APIRequestError(
                    f"Failed to fetch {method}, status code: {response.status_code}")

            data = response.json()
            self.cookies.update(response.cookies.__dict__.copy())
            if "error" in data and data["error"]:
                error_type = list(data["error"].keys())[0]
                error_message = data["error"][error_type]

                raise APIRequestError(
                    "{0} : {1}".format(error_type, error_message))

        return data

    async def _legacy_search(self, method: str, query: str, limit: int = 30, index: int = 0) -> list:
        """
        Performs a search using the legacy API.

        Parameters:
        ----------
            method (str): The API method to call for the search.
            query (str): The keyword to search for.
            limit (int, optional): The maximum number of results to return. Default is 30.
            index (int, optional): The offset for the search results. Default is 0.

        Returns:
        ----------
            list: A list of search results. Each result is a dictionary containing the relevant data.

        Raises:
        ----------
            APIRequestError: If there is an error with the API request.
        """
        query = clean_query(query)

        data = await self._legacy_api_call(method, {
            "q": query,
            "limit": limit,
            "index": index
        })

        return data["data"]

    async def _legacy_api_call(self, method, params={}):
        """
        Makes an asynchronous API call to the Deezer Legacy API.

        Parameters:
        ----------
            method (str) The API method to call.
            params (dict, optional): Additional parameters to pass to the API call. Defaults to an empty dictionary.

        Returns:
        ----------
            dict: The JSON response from the API call.

        Raises:
        ----------
            APIRequestError: If the API call fails or returns an error.
        """
        url = "{0}/{1}".format(api_urls.LEGACY_API_URL, method)

        async with httpx.AsyncClient(headers=networking_settings.HTTP_HEADERS, params=params, cookies=await self.get_cookies()) as client:
            response = await client.get(url)
            data = response.json()

        if "error" in data and data["error"]:
            error_type = list(data["error"].keys())[0]
            error_message = data["error"][error_type]
            raise APIRequestError(
                "{0} : {1}".format(error_type, error_message))

        return data

    async def get_user_data(self, update: bool = False) -> dict:
        """
        Gets the data of the user or login if it's not already in, this will only work if arl is the cookie.

        Parameters:
        ----------
            update (bool, optionalЖ): If True, the function will update the user data even if it's already available. Default is False.

        Returns:
        ----------
            dict: A dictionary containing the user data. The dictionary will include keys such as 'id', 'name', 'arl', and 'image'.

        Raises:
        ----------
            LoginError: Will raise if the arl given is not identified by Deezer.
            APIRequestError: If the API call fails or returns an error.
        """
        if self.token is not None and self.user is not None and update is False:
            return self.user

        data = await self._api_call(api_methods.GET_USER_DATA)
        data = data['results']
        self.token = data["checkForm"]

        if not data["USER"]["USER_ID"]:
            raise LoginError("Arl is invalid.")

        raw_user = data["USER"]

        if raw_user["USER_PICTURE"]:
            self.user = {
                "id": raw_user["USER_ID"],
                "name": raw_user["BLOG_NAME"],
                "arl": self.cookies["arl"],
                "image": f"https://e-cdns-images.dzcdn.net/images/user/{raw_user['USER_PICTURE']}/250x250-000000-80-0-0.jpg"
            }
        else:
            self.user = {
                "id": raw_user["USER_ID"],
                "name": raw_user["BLOG_NAME"],
                "arl": self.cookies["arl"],
                "image": "https://e-cdns-images.dzcdn.net/images/user/250x250-000000-80-0-0.jpg"
            }

        return self.user

    """
        ALBUMS
    """

    async def get_album(self, album_id: str) -> dict:
        """
        Gets the album data of the given album_id.

        Parameters:
        ----------
            album_id (str): The unique identifier of the album.

        Returns:
        ----------
            dict: A dictionary containing the album data. The dictionary will include keys such as 'cover_small', 'cover_id', etc.

        Raises:
        ----------
            APIRequestError: If there is an error with the API request.

        Note:
        ----------
            This function uses the legacy API to fetch the album data. It extracts the cover_id from the 'cover_small' URL if available,
            otherwise it sets the cover_id to -1.
        """

        data = await self._legacy_api_call(f"/album/{album_id}")
        if data["cover_small"]:
            data["cover_id"] = str(data["cover_small"]).split(
                "cover/")[1].split("/")[0]
        else:
            data["cover_id"] = -1

        return data

    async def get_album_poster(self, album: dict, size: int = 500, ext: Literal['jpg', 'png'] = "jpg") -> bytes:
        """
        Gets the album poster as a binary data.

        Parameters:
        ----------
            album (dict): Album data. This dictionary should contain the 'cover_id' key.
            size (int, optional): Size of the image, {size}x{size}. Default is 500.
            ext (str, optional): Extension of the image, can be ('.jpg' or '.png'). Default is 'jpg'.

        Returns:
        ----------
            bytes: Binary data of the image.

        Raises:
        ----------
            ValueError: If the provided extension is not 'jpg' or 'png'.
            APIRequestError: If there is an error with the API request.

        Note:
        ----------
            This function uses the '_get_poster' method to fetch the album poster.
            It passes the 'cover_id', 'ize', and 'ext' parameters to '_get_poster'.
        """
        return await self._get_poster(album["cover_id"], size=size, ext=ext)

    async def _get_poster(self, poster_id: int, size: int = 500, ext: Literal['jpg', 'png'] = "jpg") -> dict:
        """
        Fetches the album poster image from the Deezer CDN.

        Parameters:
        ----------
            poster_id (int): The unique identifier of the album cover.
            size (int, optional): The size of the image, default is 500.
            ext (Literal['jpg', 'png'], optional): The extension of the image, can be 'jpg' or 'png', default is 'jpg'.

        Returns:
        ----------
            dict: A dictionary containing the image data, including 'image' (binary data), 'ize' (tuple), 'ext' (str), and 'ime_type' (str).

        Raises:
        ----------
            ValueError: If the provided extension is not 'jpg' or 'png'.
            APIRequestError: If there is an error with the API request to fetch the album poster.
        """
        ext = ext.lower()
        if ext != "jpg" and ext != "png":
            raise ValueError("Image extension should only be jpg or png!")
        if poster_id == -1:
            url = "https://static.vecteezy.com/system/resources/thumbnails/022/059/000/small/no-image-available-icon-vector.jpg"
        else:
            url = f'https://e-cdns-images.dzcdn.net/images/cover/{
                poster_id}/{size}x{size}.{ext}'

        async with httpx.AsyncClient(headers=networking_settings.HTTP_HEADERS, cookies=await self.get_cookies()) as client:
            res = await client.get(url)
            if res.status_code != 200:
                raise APIRequestError(
                    f"Failed to fetch album poster, status code: {res.status_code}")

            image_bytes = res.read()

            return {
                "image": image_bytes,
                "size": (size, size),
                "ext": ext,
                "mime_type": "image/jpeg" if ext == "jpg" else "image/png"
            }

    async def get_album_tracks(self, album_id: str) -> list:
        """
        Gets the tracks of the given album_id.

        Parameters:
        ----------
            album_id (str): The unique identifier of the album.

        Returns:
        ----------
            list: A list of tracks.

        Raises:
        ----------
            APIRequestError: If the API call fails or returns an error.
        """

        data = await self._api_call(api_methods.ALBUM_TRACKS, params={
            "ALB_ID": album_id,
            "NB": -1
        })

        for i, track in enumerate(data["results"]["data"]):
            track["_POSITION"] = i + 1

        return data["results"]["data"]

    async def search_albums(self, query:str, limit:int=30, index:int=0)->list:
        """
        Searches albums on a given query.

        This function uses the Deezer Legacy API to perform a search for albums based on the provided query.
        It returns a list of albums that match the search criteria.

        Parameters:
        ----------
            query (str): The keyword to search for.
            limit (int, optional): The maximum number of results to return. Default is 30.
            index (int, optional): The offset for the search results. Default is 0.

        Returns:
        ----------
            list: A list of albums that match the search criteria. Each album is represented as a dictionary.

        Raises:
        ----------
            APIRequestError: If there is an error with the API request.
        """

        return await self._legacy_search(api_methods.SEARCH_ALBUM, query, limit=limit, index=index)

    """
        TRACKS
    """

    async def search_tracks(self, query: str, limit: int = 30, index: int = 0) -> list:
        """
        Searches tracks on a given query.

        This function uses the Deezer API to perform a search for tracks based on the provided query.
        It returns a list of tracks that match the search criteria.

        Parameters:
        ----------
            query (str): The keyword to search for.
            limit (int, optional): The maximum number of results to return. Default is 30.
            index (int, optional): The offset for the search results. Default is 0.

        Returns:
        ----------
            list: A list of tracks that match the search criteria. Each track is represented as a dictionary.

        Raises:
        ----------
            APIRequestError: If there is an error with the API request.
        """

        return await self._legacy_search(api_methods.SEARCH_TRACK, query, limit=limit, index=index)

    async def get_track_tags(self, track:dict, separator:str=", ", with_cover: bool = True):
        """
        Gets the possible ID3 tags of the track.

        Arguments:
        ----------
            track (dict): Track dictionary, similar to the {info} value that is returned {using get_track()}

        Parameters:
        ----------
            separator (str): Separator to separate multiple artists (default: {", "})
            with_cover (bool): If True, the function will fetch the album cover (default: {True})

        Returns:
        ----------
            dict: A dictionary containing the ID3 tags of the track.
        """

        track = track["DATA"] if "DATA" in track else track

        album_data = await self.get_album(track["ALB_ID"])

        if "main_artist" in track["SNG_CONTRIBUTORS"]:
            main_artists = track["SNG_CONTRIBUTORS"]["main_artist"]
            artists = main_artists[0]
            for i in range(1, len(main_artists)):
                artists += separator + main_artists[i]
        else:
            artists = track["ART_NAME"]

        title: str = track["SNG_TITLE"]

        if "VERSION" in track and track["VERSION"] != "":
            title += " " + track["VERSION"]

        def should_include_featuring():
            feat_keywords = ["feat.", "featuring", "ft."]

            for keyword in feat_keywords:
                if keyword in title.lower():
                    return False
            return True

        if should_include_featuring() and "featuring" in track["SNG_CONTRIBUTORS"]:
            featuring_artists_data = track["SNG_CONTRIBUTORS"]["featuring"]
            featuring_artists = featuring_artists_data[0]
            for i in range(1, len(featuring_artists_data)):
                featuring_artists += separator + featuring_artists_data[i]

            title += f" (feat. {featuring_artists})"

        total_tracks = album_data["nb_tracks"]
        track_number = str(track["TRACK_NUMBER"]) + "/" + str(total_tracks)

        if with_cover:
            cover = await self.get_album_poster(album_data, size=1000)

        tags = {
            "title": title,
            "artist": artists,
            "genre": None,
            "album": track["ALB_TITLE"],
            "albumartist": track["ART_NAME"],
            "label": album_data["label"],
            "date": track["PHYSICAL_RELEASE_DATE"],
            "discnumber": track["DISK_NUMBER"],
            "tracknumber": track_number,
            "isrc": track["ISRC"],
            "copyright": track["COPYRIGHT"],
            "_albumart": cover if with_cover else None,
        }

        if len(album_data["genres"]["data"]) > 0:
            print(album_data["genres"])
            tags["genre"] = album_data["genres"]["data"][0]["name"]

        if "author" in track["SNG_CONTRIBUTORS"]:
            _authors = track["SNG_CONTRIBUTORS"]["author"]

            authors = _authors[0]
            for i in range(1, len(_authors)):
                authors += separator + _authors[i]

            tags["author"] = authors

        return tags
