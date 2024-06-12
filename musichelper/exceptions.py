class ServiceUnavailable(Exception):
    def __init__(self, service: str) -> None:
        self.service:str = service
        super().__init__(f"The '{service}' service is unavailable")


class UnknownService(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class FFmpegNotFoundError(Exception):
    """Exception raised if ffmpeg is not found."""
    pass


class DownloadLinkNotFoundError(Exception):
    """Exception called if the download link was not found."""
    pass


class FFmpegConversionError(Exception):
    """Exception called if ffmpeg failed to convert the file."""

    def __init__(self, stderr: str):
        self.stderr = stderr
        super().__init__(f"Conversion error: \n{stderr}")


class NoResultsFound(Exception):
    def __init__(self, query:str=None, service:str=None) -> None:
        self.query: str = query
        self.service: str = service
        if self.query is not None and self.service is not None:
            super().__init__(f"Nothing could be found for the query `{query}` on the service `{service}`")
        else:
            super().__init__("Nothing found...")

class InvalidVideoId(Exception):
    def __init__(self, video_id:str) -> None:
        self.video_id:str = video_id
        super().__init__(f"Invalid YouTube video id: {video_id}")


class APIRequestError(Exception):
    def __init__(self, error:str="") -> None:
        self.error:str = error
        super().__init__(f"Error while interacting with API: {error}")

class LoginError(Exception):
    def __init__(self, error:str="") -> None:
        self.error:str = error
        super().__init__(f"Login error: {error}")

