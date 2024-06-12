# music-helper | v`3.0.0b`

# About
The library lets you interact with various music services in an asynchronous way. You can search, download tracks, and so on.

# Installation
`pip install music-helper`

# Usage
## Initialization and settings
```python
import asyncio
from musichelper import MusicHelper
from musichelper.soundcloud import SoundCloudAuth
from musichelper.util import Parameters

async def main():
    parameters = Parameters(
        debug=True,
        sc_oauth=SoundCloudAuth(
            client_id="-",
            auth_token="-"
        ),
        yt_oauth=True
    )
    helper = MusicHelper(parameters)

if __name__ == "__main__":
    asyncio.run(main())
```
### Description of module settings (Parameters)
|Argument|Type|Default|Description|
|-|-|-|-|
|debug|bool|False|Enable debugging mode|
|loop|AbstractEventLoop|-|Loop the application if `None` is taken automatically|
|sc_oauth|SoundCloudAuth|-|SoundCloud Settings Instance|
|yt_oauth|bool|False|Whether to enable authorization for YouTube. For 18+ video tracks|
|deezer_arl|str|-|Deezer ARL token, to access the Deezer API|
|ffmpeg_path|str|-|Path to the ffmpeg binary if you leave `None` in the environment variables|




## Module logging
```python
import asyncio
from musichelper import MusicHelper
from musichelper.soundcloud import SoundCloudAuth
from musichelper.util import Parameters

async def main():
    user_logger = logging.getLogger('user_application')
    user_logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    user_logger.addHandler(console_handler)
    
    musichelper_logger = logging.getLogger('musichelper')
    user_logger.addHandler(console_handler)  
    musichelper_logger.addHandler(console_handler) 

    parameters = Parameters(
        debug=True,
        sc_oauth=SoundCloudAuth(
            client_id="-",
            auth_token="-"
        ),
        yt_oauth=True
    )
    helper = MusicHelper(parameters)

if __name__ == "__main__":
    asyncio.run(main())
```


The following loggers are available in the module
|Name|Description|
|-|-|
|musichelper|Main module logger. Includes all logs of submodules|
|musichelper.deezer|Submodule logger for Deezer platform|
|musichelper.youtube|Submodule logger for YouTube platform|
|musichelper.soundcloud|Submodule logger for SoundCloud platform|


## Searching and downloading
```python
query = "daegho - i want u"
results = await helper.search(query, service="soundcloud", limit=1)

for result in results:
    await results.download(filename="daegho - i want u")
```

### Using services for search
The `service` parameter of the `search` function accepts the key of the service to be searched, but it can also accept multiple services - then the search will be performed on all services available in the list. In this case, the query limit is `distributed equally across all services`.

In the case of searches from different services, it will not return a list, but a dictionary with format results:
```json
{
    "deezer": [<DeezerTrack object at 0x00001>, <DeezerTrack object at 0x00002>],
    "soundcloud": [<SoundCloudTrack object at 0x00003>, <SoundCloudTrack object at 0x00003>],
    "youtube": [<YouTubeTrack object at 0x00004>, <YouTubeTrack object at 0x00005>]
}
```

#### Available services
|Key|Name|
|-|-|
|soundcloud|SoundCloud|
|deezer|Deezer|
|youtube|YouTube|
|**ytm**|**YouTube Music**|
**p.s:** YouTube Music is currently unavailable

# Exceptions
|Name|Arguments|Description|
|-|-|-|
|ServiceUnavailable|service: str|The '{service}' service is unavailable|
|UnknownService|-|-|
|FFmpegNotFoundError|-|Exception raised if ffmpeg is not found.|
|DownloadLinkNotFoundError|-|Exception called if the download link was not found.|
|FFmpegConversionError|stderr: str|Exception called if ffmpeg failed to convert the file.|
|NoResultsFound|query: str, service: str|Nothing could be found for the query {query} on the service {service}. If either query or service is not provided, it raises "Nothing found...".|
|InvalidVideoId|video_id: str|Invalid YouTube video id: {video_id}|

