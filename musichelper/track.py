from typing import Any
from musichelper.exceptions import DownloadLinkNotFoundError, FFmpegConversionError, InvalidVideoId, UnknownService
from musichelper.soundcloud import SoundCloud
from asyncio import subprocess
import os, shutil, logging, asyncio, aiohttp
from soundcloud.resource.aliases import Track as SCTrack
from musichelper.util import Parameters
from musichelper.youtube import YouTube
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import mutagen
from mutagen.id3 import ID3, APIC


class TrackMetadata:
    def __init__(self, artist: str = None, title: str = None,
                 album: str = None, cover_url: str = None) -> None:
        self.artist: str = artist
        self.title: str = title
        self.album: str = album
        self.cover_url: str = cover_url

        self.release_year: int = -1
        self.genres: str = ""

    def fix(self):
        # -----------
        """
        Fix the title of the track by removing the artist name from the title.

        This method is used to ensure that the track title does not contain the artist's name twice.
        It finds the artist's name in the title, removes it, and adjusts the album name if necessary.
        """
        lower_title = self.title.lower()
        lower_artist = self.artist.lower()

        artist_index = lower_title.find(lower_artist)
        if artist_index != -1:
            end_index = artist_index + len(lower_artist)
            while end_index < len(lower_title) and lower_title[end_index] in ['-', ' ']:
                end_index += 1

            new_title = self.title[:artist_index] + self.title[end_index:]
            new_title = new_title.strip()

            if self.title == self.album:
                self.album = new_title

            self.title = new_title

    def to_dict(self):
        """
        Returns a dictionary representation of the TrackMetadata object.

        Parameters:
        -----------
            None

        Returns:
        -----------
            dict: A dictionary containing the artist, title, album, and cover_url of the track.

        Example:
        -----------
            >>> metadata = TrackMetadata("Artist", "Title", "Album", "Cover URL")
            >>> metadata.to_dict()
            {
                "artist": "Artist",
                "title": "Title",
                "album": "Album",
                "cover_url": "Cover URL",
                "release_year": "Release year",
                "genres": "Genres
            }
        """
        return {
            "artist": self.artist,
            "title": self.title,
            "album": self.album,
            "cover_url": self.cover_url,
            "release_year": self.release_year,
            "genres": self.genres
        }


class Track:
    def __init__(self) -> None:
        self._download_link: str = ""
        self.session = None
        self.metadata: TrackMetadata = TrackMetadata()
        self.downloadeble = False

    async def download(self, destination: str = None, filename: str = None) -> str:
        """
        Download the track.

        This method is responsible for downloading the track from the source and saving it to the specified destination.
        If no destination is provided, the track will be saved in the current working directory.
        If no filename is provided, the track will be saved with a default name based on the track's metadata.

        Parameters:
        -----------
            destination (str, optional): The destination directory where the track will be saved. If not provided, the track will be saved in the current working directory.
            filename (str, optional): The name of the file where the track will be saved. If not provided, the track will be saved with a default name based on the track's metadata.

        Returns:
        -----------
            str: The path of the downloaded track.

        Raises:
        -----------
            NotImplementedError: If the download method is not overridden in the subclasses.
        """

        raise NotImplementedError(
            "Download method must be overridden in subclasses")

    async def download_image(self, url: str) -> bytes:
        """
        Downloads an image from the provided URL using `aiohttp`.

        Parameters:
        -----------
            url (`str`): The URL of the image to download.

        Returns:
        -----------
            `bytes`: The downloaded image data in bytes. If the download fails, returns None.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    return None

    async def edit_tags(self, file_path: str) -> bool:
        """
        Edits the ID3 tags of the audio file located at the given file_path.

        Parameters:
        -----------
            file_path (`str`): The path to the audio file.

        Returns:
        -----------
            bool: True if the tags were edited successfully, False otherwise.

        Example:
        -----------
            >>> track = Track()
            >>> track.metadata = TrackMetadata("Artist", "Title", "Album", "Cover URL", 2022, "Genre")
            >>> track.edit_tags("path/to/audio.mp3")
            True

        Note:
        -----------
            This function clears all existing tags, then adds new tags based on the track's metadata.
            If the release year or genres are available, they are added as TDRC and TCON tags, respectively.
            If the cover URL is available, it downloads the image and adds it as an APIC tag.
        """

        audio = ID3(file_path)
        if audio is None:
            return False

        audio.clear()
        audio.add(mutagen.id3.TIT2(encoding=3, text=self.metadata.title))
        audio.add(mutagen.id3.TPE1(encoding=3, text=self.metadata.artist))
        audio.add(mutagen.id3.TALB(encoding=3, text=self.metadata.album))
        if self.metadata.release_year != -1:
            audio.add(mutagen.id3.TDRC(
                encoding=3, text=self.metadata.release_year))
        if len(self.metadata.genres) > 0:
            audio.add(mutagen.id3.TCON(
                encoding=3, text=self.metadata.genres))
            # audio.add(mutagen.id3.TCON(
            #     encoding=3, text=', '.join(self.metadata.genres)))
        if self.metadata.cover_url:
            image_data = await self.download_image(self.metadata.cover_url)
            if image_data:
                image_mime = 'image/jpeg'
                image_type = mutagen.id3.PictureType.COVER_FRONT
                image_desc = 'Cover Art'
                audio.add(APIC(encoding=3, mime=image_mime,
                               type=image_type, desc=image_desc, data=image_data))

        audio.save()
        return True

    async def download_file(self, destination: str = None, filename: str = None) -> str:
        """
            Downloads the track from the provided download link, converts it to MP3 format, and saves it to the specified destination.

            Parameters:
            -----------
                destination (str, optional): The destination directory where the track will be saved. If not provided, the track will be saved in the current working directory.
                filename (str, optional): The name of the file where the track will be saved. If not provided, the track will be saved with a default name based on the track's metadata.

            Returns:
            -----------
                str: The path of the downloaded and converted track.

            Raises:
            -----------
                RuntimeError: If ffmpeg is not found in the system's PATH.
                DownloadLinkNotFoundError: If no download link is available.
                FFmpegConversionError: If an error occurs during the ffmpeg conversion process.
        """
        musichelper_logger = logging.getLogger('musichelper')
        if not shutil.which("ffmpeg", path=Parameters.get_instance().ffmpeg_path):
            musichelper_logger.critical('Could not find ffmpeg...')
            raise RuntimeError(
                "ffmpeg is not found. Install ffmpeg and make sure it is available in the PATH.")
        if not self._download_link:
            musichelper_logger.error(
                "Download not possible, no download link....")
            raise DownloadLinkNotFoundError("No download link found.")
        if destination is None:
            destination = "./"

        if filename:
            if not ".mp3" in filename:
                filename += ".mp3"
        else:
            filename = f"{self.metadata.artist} - {self.metadata.title}.mp3"
        musichelper_logger.info(
            "Start downloading track `%s` to `%s`", filename, destination)
        output_path = os.path.join(destination, filename)
        try:

            process = await asyncio.create_subprocess_exec(
                'ffmpeg', '-y', '-i', self._download_link, '-vn', '-ar', '44100', '-ac', '2', '-b:a', '192k', output_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                musichelper_logger.error(
                    "Failed to download track: %s", stderr.decode())
                raise FFmpegConversionError(stderr.decode())

            if Parameters.get_instance().debug:
                musichelper_logger.debug(
                    "Editing audio tags for `%s`", filename)
            await self.edit_tags(output_path)
            musichelper_logger.info(
                "Track `%s` successfully downloaded to `%s`", filename, destination)
            return output_path
        except Exception as e:
            raise FFmpegConversionError(str(e))

    def to_dict(self) -> dict:
        return {
            "downloadeble": self.downloadeble,
            "metadata": self.metadata.to_dict()
        }


class SoundCloudTrack(Track):
    def __init__(self) -> None:
        super().__init__()
        self.track_id: int = -1

    def to_dict(self):
        data = super().to_dict()
        data['track_id'] = self.track_id
        return data

    async def download(self, destination: str = None, filename: str = None) -> str:
        """
        Downloads the track from SoundCloud and saves it to the specified destination.

        Parameters:
        -----------
            destination (str, optional): The destination directory where the track will be saved. If not provided, the track will be saved in the current working directory.
            filename (str, optional): The name of the file where the track will be saved. If not provided, the track will be saved with a default name based on the track's metadata.

        Returns:
        -----------
            str: The path of the downloaded track.

        Raises:
        -----------
            DownloadLinkNotFoundError: If the download link could not be retrieved or if track information is missing.
            RuntimeError: If ffmpeg is not found in the system's PATH.
            FFmpegConversionError: If an error occurs during the ffmpeg conversion process.
        """

        soundcloud = SoundCloud()
        self._download_link = await soundcloud.get_track_url(self.track_id)
        if not self._download_link:
            raise DownloadLinkNotFoundError(
                "Failed to retrieve download URL or track information.")
        self.downloadeble = True
        return await self.download_file(
            destination=destination,
            filename=filename
        )


class YouTubeTrack(Track):
    def __init__(self) -> None:
        super().__init__()
        self.video_id: int = -1

    def to_dict(self):
        data = super().to_dict()
        data['video_id'] = self.video_id
        return

    async def download(self, destination: str = None, filename: str = None):
        """
        Downloads the track from YouTube (YT Music) and saves it to the specified destination.

        Parameters:
        -----------
            destination (str, optional): The destination directory where the track will be saved. If not provided, the track will be saved in the current working directory.
            filename (str, optional): The name of the file where the track will be saved. If not provided, the track will be saved with a default name based on the track's metadata.

        Returns:
        -----------
            str: The path of the downloaded track.

        Raises:
        -----------
            DownloadLinkNotFoundError: If the download link could not be retrieved or if track information is missing.
            RuntimeError: If ffmpeg is not found in the system's PATH.
            FFmpegConversionError: If an error occurs during the ffmpeg conversion process.
        """

        youtube = YouTube()
        self._download_link = await youtube.get_audio_stream(self.video_id)
        self.downloadeble = True
        return await self.download_file(
            destination=destination,
            filename=filename
        )


class DirectTrack(Track):
    """
        ## ^_^
        I refuse to comment on that xD
    """

    def __init__(self) -> None:
        super().__init__()
        self.site_url: str = ""
        self.session = ""

    def _make_session(self):
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': UserAgent().random})

    async def _close_session(self):
        if not self.session is None:
            await self.session.close()

    @staticmethod
    async def from_site(site_link: str, error: bool = True,
                        parse_a: bool = True) -> Track | None:
        track = DirectTrack()
        track._make_session()
        track.metadata = TrackMetadata(
            "unknown",
            "unknown",
            "unknown",
            None
        )
        track.site_url = site_link
        async with track.session.get(track.site_url) as response:
            if response.status == 200:
                page_content = await response.text()
                await track._close_session()
            else:
                await track._close_session()
                # del track
                if error:
                    raise DownloadLinkNotFoundError(
                        "Failed to retrieve download URL.")
                else:
                    return None

        soup = BeautifulSoup(page_content, "html.parser")
        if parse_a is True:
            mp3_links = soup.find_all("a")
            for link in mp3_links:
                if link.href and link.href.endswith(".mp3"):
                    track._download_link = link.href
                    break

        if track._download_link == "":
            play_btns = soup.find_all('div', class_='play-btn')
            for play_btn in play_btns:
                link: str = play_btn.get('href')
                if link:
                    if link.endswith(".mp3"):
                        track._download_link = link
                        break

        if track._download_link == "":
            # del track
            if error:
                raise DownloadLinkNotFoundError(
                    "Failed to retrieve download URL.")
            else:
                return None
        return track

    def to_dict(self):
        data = super().to_dict()
        data['site_url'] = self.site_url
        return

    async def download(self, destination: str = None, filename: str = None):
        self.downloadeble = True
        return await self.download_file(
            destination=destination,
            filename=filename
        )


class TrackFactory:
    """
    Factory class to create different types of Track objects.
    """

    @staticmethod
    def create_track(data: Any, factory: str = None) -> SoundCloudTrack | YouTubeTrack:
        """
        Create a Track object based on the provided data and factory.

        Parameters:
        -----------
            data (Any):The data used to create the Track object.
            factory (str, optional): The factory to use for creating the Track object.

        Returns:
        -----------
            (SoundCloudTrack | YouTubeTrack): The created Track object.

        Raises:
        -----------
            ValueError: If the provided data and factory do not match any known combination.
        """
        if factory == "soundcloud" and isinstance(data, SCTrack):
            track = SoundCloudTrack()
            track.track_id = data.id
            track.metadata = TrackMetadata(
                artist=data.user.username,
                title=data.title,
                album=data.title,
                cover_url=data.artwork_url
            )
            track.metadata.release_year = data.display_date
            track.metadata.genres = data.genre
            return track
        elif factory == "yt" and isinstance(data, dict) and isinstance(data.get('id'), str):
            track = YouTubeTrack()
            track.video_id = data['id']
            track.metadata = TrackMetadata(
                artist=data['channel']['name'],
                title=data['title'],
                album=data['title'],
                cover_url=data['thumbnails'][-1]['url']
            )
            track.metadata.fix()
            return track
        elif factory == "ytm":
            ...
        elif factory == "deezer":
            ...
        elif factory == "direct":
            ...
        else:
            if isinstance(data, SCTrack):
                track = SoundCloudTrack()
                track.track_id = data.id
                track.metadata = TrackMetadata(
                    artist=data.user.username,
                    title=data.title,
                    album=data.title,
                    cover_url=data.artwork_url
                )
                return track
            elif isinstance(data, dict):
                ...
