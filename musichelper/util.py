import logging
import re
from asyncio import AbstractEventLoop, get_event_loop
from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from musichelper.soundcloud import SoundCloudAuth


def is_service(url: str) -> dict:
    """
        This function determines the service (YouTube, YouTube Music, SoundCloud, Spotify) 
        from a given URL and extracts the relevant identifiers.

        Parameters:
            url (str): The URL to be analyzed.

        Returns:
            dict: A dictionary containing the service name and relevant identifiers. 
                If the URL does not match any known service, returns None.

        Example:
            >>> is_service('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
            {'service': 'youtube', 'id': 'dQw4w9WgXcQ'}
            >>> is_service('https://music.youtube.com/watch?v=dQw4w9WgXcQ')
            {'service': 'youtube_music', 'id': 'dQw4w9WgXcQ'}
            >>> is_service('https://soundcloud.com/user/track')
            {'service': 'oundcloud', 'user_id': 'user', 'track_id': 'track'}
            >>> is_service('https://open.spotify.com/track/1234567890')
            {'service': 'spotify', 'id': '1234567890'}
    """

    # YouTube
    youtube_regex = r'(?:https?://)?(?:www\.)?youtu(?:\.be/|be\.com/\S*?[\?\&]v=)([a-zA-Z0-9_-]{11})(?:[^\w\-]|$)'
    match = re.search(youtube_regex, url)
    if match:
        return {'service': 'youtube', 'id': match.group(1)}

    # YouTube Music
    youtube_music_regex = r'(?:https?://)?music\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})(?:[^\w\-]|$)'
    match = re.search(youtube_music_regex, url)
    if match:
        return {'service': 'youtube_music', 'id': match.group(1)}

    # SoundCloud
    soundcloud_regex = r'(?:https?://)?(?:www\.)?soundcloud\.com/([\w-]+)/([\w-]+)'
    match = re.search(soundcloud_regex, url)
    if match:
        return {'service': 'soundcloud', 'user_id': match.group(1), 'track_id': match.group(2)}

    # Spotify
    spotify_regex = r'(?:https?://)?(?:open\.spotify\.com/|spotify\.com/)(?:track|album)/([a-zA-Z0-9]+)'
    match = re.search(spotify_regex, url)
    if match:
        return {'service': 'spotify', 'id': match.group(1)}

    return None


class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class Parameters(metaclass=SingletonMeta):
    _instance: Optional['Parameters'] = None

    def __init__(self, debug: bool = False, loop: AbstractEventLoop = None,
                 sc_oauth: 'SoundCloudAuth' = None, yt_oauth: bool = False,
                 deezer_arl: str = None, deezer_cache:bool=False,
                 ffmpeg_path: str = None) -> None:
        """
        Initialize Parameters instance.

        Parameters:
        -----------
            debug (bool, optional): Flag to enable debug mode. Defaults to False.
            loop (AbstractEventLoop, optional): Event loop instance. If not provided, it will use the default event loop. Defaults to None.
            deezer_arl (str, optional): Deezer ARL key. Defaults to None.
            deezer_cache (bool, optional): Whether Deezer authorization is cached. Defaults to False.
            sc_oauth (SoundCloudAuth, optional): SoundCloud OAuth instance. Defaults to None.
            yt_oauth (bool, optional): Flag to enable YouTube OAuth. Defaults to False.
            ffmpeg_path (str, optional): Path to the ffmpeg executable. Defaults to None.

        Returns:
        -----------
            None
        """

        self.debug: bool = debug
        self.sc_oauth: 'SoundCloudAuth' = sc_oauth
        self.yt_oauth: bool = yt_oauth
        self.deezer_arl: str = deezer_arl
        self.deezer_cache:bool = deezer_cache
        self.loop: AbstractEventLoop = loop or get_event_loop()
        self.ffmpeg_path: str = ffmpeg_path

    @classmethod
    def get_instance(cls, *args, **kwargs) -> 'Parameters':
        """
        This method returns the singleton instance of the Parameters class.
        If no instance exists, it creates a new one.

        Parameters:
        -----------
            *args : tuple
                Variable length argument list. Passed to the constructor of the class.
            **kwargs : dict
                Arbitrary keyword arguments. Passed to the constructor of the class.

        Returns:
        --------
            Parameters : Parameters
                The singleton instance of the Parameters class.

        Raises:
        -------
            None

        Examples:
        ---------
            >>> Parameters.get_instance(debug=True)
            <Parameters instance at 0x000001>
            >>> Parameters.get_instance()
            <Parameters instance at 0x000001>
        """

        if cls._instance is None:
            cls._instance = cls(*args, **kwargs)
        return cls._instance


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    This function sets up a logger with the given name and level.

    Parameters:
    -----------
        name (str): The name of the logger.
        level (int, optional): The logging level. Defaults to logging.INFO.

    Returns:
    --------
        logging.Logger: The configured logger instance.

    Examples:
    ---------
        >>> setup_logger('my_logger', logging.DEBUG)
        <Logger my_logger (DEBUG)>
        >>> setup_logger('my_logger')
        <Logger my_logger (INFO)>
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger


def clean_query(query: str) -> str:
    # A pure copy-paste of regex patterns from DeezloaderRemix
    # I dont know regex

    # And I copied it from acgonzales/pydeezer
    # I don't understand regex at all either, what a coincidence

    query = re.sub(r"/ feat[\.]? /g", " ", query)
    query = re.sub(r"/ ft[\.]? /g", " ", query)
    query = re.sub(r"/\(feat[\.]? /g", " ", query)
    query = re.sub(r"/\(ft[\.]? /g", " ", query)
    query = re.sub(r"/\&/g", "", query)
    query = re.sub(r"/–/g", "-", query)
    query = re.sub(r"/–/g", "-", query)
    return query
