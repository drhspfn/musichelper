import asyncio, math, aiohttp, itertools
from logging import Logger, DEBUG, INFO
from typing import List, Optional, Tuple
from soundcloud import SoundCloud as Sound_Cloud
from concurrent.futures import ThreadPoolExecutor
from soundcloud.resource.aliases import SearchItem
from soundcloud.resource.track import BasicTrack, Track
from musichelper.util import Parameters, SingletonMeta, setup_logger


class SoundCloudAuth:
    def __init__(self, client_id: str, auth_token: str) -> None:
        """
        Initialize SoundCloudAuth instance with client_id and auth_token.

        Parameters:
            client_id (str): The client_id for SoundCloud API.
            auth_token (str): The auth_token for SoundCloud API.

        Returns:
            None: This method does not return anything.
        """
        self.client_id = client_id
        self.auth_token = auth_token


class SoundCloud(metaclass=SingletonMeta):
    def __init__(self, loop:asyncio.AbstractEventLoop, client_id: str = None,
                 auth_token: str = None,
                 user_agent: str = None) -> None:
        self.loop:asyncio.AbstractEventLoop = loop
        if user_agent is None:
            self.__soundcloud = Sound_Cloud(
                client_id=client_id,
                auth_token=auth_token
            )

        else:
            self.__soundcloud = Sound_Cloud(
                client_id=client_id,
                auth_token=auth_token,
                user_agent=user_agent
            )
            
        self.is_debug = Parameters().get_instance().debug
        self.logger:Logger = setup_logger("musichelper.soundcloud", level=DEBUG if self.is_debug else INFO)
        # self.debug("[SC.__init__]: The SoundCloud module has been successfully initialized")
        self.logger.info("SoundCloud initialized")
        
    def debug(self, msg:str, *args:object):
        if self.is_debug:
            self.logger.debug(msg, *args)

    async def get_track(self, track_id: str) -> Optional[BasicTrack]:
        """
        Returns the track with the given track_id.
        If the ID is invalid, return None
        """
        # loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            track = await self.loop.run_in_executor(executor, self.__soundcloud.get_track, track_id)
        return track

    async def resolve(self, link: str) -> Optional[SearchItem]:
        """
        Resolves the given URL to a SoundCloud resource.

        This function uses the SoundCloud API to resolve the provided URL.
        It uses a ThreadPoolExecutor to run the resolution operation in a separate thread,
        allowing for non-blocking execution.

        Parameters:
        -----------
            link (str): The URL to be resolved.

        Returns:
        -----------
            soundcloud.resource.Track | soundcloud.resource.Playlist | soundcloud.resource.User | None:
                Returns the resolved resource if the URL is valid and points to a SoundCloud resource.
                Returns None if the URL is invalid or does not point to a SoundCloud resource.
        """
        # loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            track = await self.loop.run_in_executor(executor, self.__soundcloud.resolve, link)
        return track

    async def search_tracks(self, query: str, limit: int = 5) -> List[Track]:
        """
        Search for tracks on SoundCloud.

        This function uses the SoundCloud API to search for tracks based on the provided query.
        It uses a ThreadPoolExecutor to run the search operation in a separate thread, allowing for non-blocking execution.

        Parameters:
        -----------
            query (str): The search query string.
            limit (int, optional): The maximum number of tracks to return. Default is 5.

        Returns:
        -----------
            list: A list of soundcloud.resource.Track objects representing the search results.
                If no tracks are found, an empty list is returned.
                If the limit parameter is set to a value greater than the number of available tracks,
                the function will return all available tracks.

        """
        self.debug("[search_tracks]: Search for %s [Limit: %d]", query, limit)
        # loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            tracks = await self.loop.run_in_executor(executor, self.__soundcloud.search_tracks, query)
        if tracks:
            self.debug("[search_tracks]: Generator length limit to %d", limit)
            tracks = list(itertools.islice(tracks, limit))
            
        return tracks

    async def get_track_original_download(self, track_id: int,
                                          token: str = None) -> Optional[str]:
        """
        Get track original download link. If track is private,
        requires secret token to be provided (last part of secret URL).

        This function uses the SoundCloud API to retrieve the original download link
        for a given track ID. If the track is private, the function requires a secret
        token to be provided. The function uses a ThreadPoolExecutor to run the
        download link retrieval operation in a separate thread, allowing for
        non-blocking execution.

        Parameters:
        -----------
            track_id (int): The ID of the track for which the download link is required.
            token (str, optional): The secret token for private tracks. Default is None.

        Returns:
        -----------
            str: The original download link for the track if the track is public or
                if the secret token is provided for private tracks.
            None: If the track ID is invalid or if the track is private and the secret
                token is not provided.
        """
        

        # loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            download_url = await self.loop.run_in_executor(executor, self.__soundcloud.get_track_original_download, track_id, token)
        return download_url

    async def get_track(self, track_id:int) ->  Optional[BasicTrack]:
        """
        Asynchronously retrieves a track from SoundCloud using the provided track_id.

        Parameters:
        -----------
            track_id (int): The unique identifier of the track to retrieve.

        Returns:
        -----------
            Optional[BasicTrack]: The retrieved track if the track_id is valid.
                                Returns None if the track_id is invalid.

        Note:
        -----------
            This function uses asyncio and ThreadPoolExecutor to perform the track retrieval
            operation in a non-blocking manner. It retrieves the track using the SoundCloud API
            and returns the result.
        """
        # loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            track = await self.loop.run_in_executor(executor, self.__soundcloud.get_track, track_id)
        return track

    async def get_track_url(self, track_id:int, return_track:bool=False) -> str | Tuple[str, SearchItem] | Tuple[None, SearchItem] | Tuple[None, None]:
        """
        Asynchronously retrieves the downloadable URL of a track from SoundCloud using the provided track_id.
        If the track is not downloadable, it attempts to find a suitable transcoding and returns its URL.
        If no suitable transcoding is found, it returns None.

        Parameters:
        -----------
            track_id (int): The unique identifier of the track to retrieve.

        Returns:
        -----------
            str: The URL of the downloadable track.
            Tuple[str, SearchItem]: A tuple containing the URL of the downloadable track and the corresponding SearchItem.
            Tuple[None, SearchItem]: A tuple containing None and the corresponding SearchItem when the track is not downloadable.
            Tuple[None, None]: A tuple containing None and None when the track_id is invalid.
        """
        self.debug('[get_track_url]: Getting the stream link for the track: %d', track_id)
        track = self.__soundcloud.get_track(track_id)
        if not track:
            self.debug('[get_track_url]: Incorrect tarck_id: %d', track)
            return (None, None) if return_track else  None

        download_url = None
        if track.downloadable:
            download_url = await self.get_track_original_download(
                track.id, track.secret_token)

        if download_url is None:
            aac_transcoding = None
            mp3_transcoding = None

            for t in track.media.transcodings:
                if t.format.protocol == "hls" and "aac" in t.preset:
                    aac_transcoding = t
                elif t.format.protocol == "hls" and "mp3" in t.preset:
                    mp3_transcoding = t

            transcoding = None

            if aac_transcoding:
                transcoding = aac_transcoding
            elif mp3_transcoding:
                transcoding = mp3_transcoding

            if not transcoding:
                self.debug('[get_track_url]: No transcoding...')
                return (None, track) if return_track else  None 

            url = transcoding.url
            bitrate_KBps = 256 / 8 if "aac" in transcoding.preset else 128 / 8
            total_bytes = bitrate_KBps * transcoding.duration

            min_size = 0
            max_size = math.inf

            if not min_size <= total_bytes <= max_size:
                return (None, track) if return_track else  None 

            if url is not None:
                headers = self.__soundcloud.get_default_headers()
                if self.__soundcloud.auth_token:
                    headers["Authorization"] = f"OAuth {
                        self.__soundcloud.auth_token}"

                self.debug('[get_track_url]: Initializing a web session...')
                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.get(url, params={"client_id": self.__soundcloud.client_id}) as response:
                        if response.status != 200:
                            self.logger.error('[get_track_url]: Negative from SoundCLoud: %d', response.status)
                            return (None, track) if return_track else  None 
                        
                        download_url = await response.json()
                        download_url = download_url.get('url', "")
                        self.debug('[get_track_url]: The broadcast link was successfully received!')

        return (download_url, track) if return_track else  download_url
