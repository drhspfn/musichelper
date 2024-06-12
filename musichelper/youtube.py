import asyncio
from concurrent.futures import ThreadPoolExecutor
from logging import Logger, DEBUG, INFO
from typing import List
from musichelper.exceptions import InvalidVideoId
from musichelper.util import Parameters, SingletonMeta, setup_logger
from youtubesearchpython.__future__ import VideosSearch
from pytube.exceptions import RegexMatchError
from pytube import YouTube as PYYouTUbe


class YouTube(metaclass=SingletonMeta):
    def __init__(self, loop: asyncio.AbstractEventLoop,  yt_oauth: bool = False) -> None:
        self.yt_oauth: bool = yt_oauth
        self.is_debug = Parameters().get_instance().debug
        self.logger:Logger = setup_logger("musichelper.youtube", level=DEBUG if self.is_debug else INFO)
        self.loop: asyncio.AbstractEventLoop = loop
        self.logger.info("YouTube initialized")

    def debug(self, msg:str, *args:object):
        if self.is_debug:
            self.logger.debug(msg, *args)

    async def get_audio_stream(self, video_id: str) -> str:
        def _get_audio_stream():
            try:
                video_object = PYYouTUbe(
                    f"https://www.youtube.com/watch?v={video_id}", use_oauth=self.yt_oauth)
            except RegexMatchError:
                self.logger.error('Incorrect video id: %d', video_id)
                raise InvalidVideoId(video_id)
            audio_url = video_object.streams.get_audio_only().url
            return audio_url


        self.logger.info("Getting an audio stream for %d", video_id)
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            aurio_url = await loop.run_in_executor(executor, _get_audio_stream)
        return aurio_url

    async def search_tracks(self, query: str, limit: int = 1) -> List[dict]:
        self.debug("Searching tracks for %s [Limit: %d]", query, limit)
        search = VideosSearch(f'{query} music', limit=limit)
        videosResult = await search.next()
        return videosResult['result']
