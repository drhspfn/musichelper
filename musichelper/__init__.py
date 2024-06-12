import logging
import math
from typing import Dict, List, Union
from musichelper.deezer import Deezer
from musichelper.util import Parameters, setup_logger
from .exceptions import NoResultsFound, ServiceUnavailable
from .soundcloud import SoundCloud
from .track import Track, TrackFactory
from .youtube import YouTube


class MusicHelper:
    def __init__(self, parameters:Parameters=None) -> None:
        """
        Initialize MusicHelper class with the provided parameters.

        Parameters:
        -----------
            parameters (Parameters, optional): An instance of Parameters class. Defaults to None. If None, it will use an empty Parameters instance.

        Returns:
        -----------
            None
        """
        
        if parameters is None: parameters = Parameters()
        self.parameters = parameters

        self.logger = setup_logger("musichelper", level=logging.DEBUG if parameters.debug else logging.INFO)
        

        self.__avaliable_services = {
            'soundcloud': "SoundCloud",
            'deezer': "Deezer",
            'yt': "YouTube",
            'ytm': "YouTube Music"
        }
        self.services: Dict[str, Union[SoundCloud, None]] = {
            service: None for service in self.__avaliable_services.keys()}
        self.services_status: Dict[str, bool] = {
            service: False for service in self.__avaliable_services.keys()}

        if parameters.sc_oauth is None:
            self.logger.info('[HELPER]: SoundCLoud initialization -> Service disabled!')
            self.services_status["soundcloud"] = False
            self.services["soundcloud"] = None
        else:
            try:
                
                self.soundcloud = SoundCloud(
                    client_id=parameters.sc_oauth.client_id,
                    auth_token=parameters.sc_oauth.auth_token,
                    loop = parameters.loop
                )
                self.services["soundcloud"] = self.soundcloud
                self.services_status["soundcloud"] = True
                self.logger.info('[HELPER]: SoundCLoud initialization -> Service connected!')
            except Exception as e:
                self.logger.info('[HELPER]: SoundCLoud initialization -> Disabled, error: %s!', str(e))
                self.services_status["soundcloud"] = False
                self.services["soundcloud"] = None

        if parameters.deezer_arl is None:
            self.logger.info('[HELPER]: Deezer initialization -> Service disabled!')
            self.services_status["deezer"] = False
            self.services["deezer"] = None
        else:
            try:
                self.deezer = Deezer(
                    arl=parameters.deezer_arl,
                    loop = parameters.loop
                )
                self.services["deezer"] = self.deezer
                self.services_status["deezer"] = True
                self.logger.info('[HELPER]: Deezer initialization -> Service connected!')
            except Exception as e:
                self.logger.info('[HELPER]: Deezer initialization -> Disabled, error: %s!', str(e))
                self.services_status["deezer"] = False
                self.services["deezer"] = None
        ### ============================================================================= ###
        ### ============================================================================= ###
        ### ============================================================================= ###
        ### ============================================================================= ###
        self.youtube = YouTube(
            yt_oauth=parameters.yt_oauth,
            loop = parameters.loop
        )
        self.logger.info('[HELPER]: YouTube initialization -> Service connected!')
        self.services["yt"] = self.youtube
        self.services_status["yt"] = True

        self._setup_submodule_loggers()
        self.logger.info("MusicHelper initialized.")


    def _setup_submodule_loggers(self):
        """
        Setup loggers for all initialized services.

        This method iterates over all initialized services (stored in self.services)
        and appends their loggers to a list. Then, it sets the 'propagate' attribute
        of each logger to True, which means that messages logged by these loggers
        will also be handled by the root logger.
        """

        submodule_loggers = []
        for v in self.services.values():
            if not v is None:
                submodule_loggers.append(v.logger)
        
        for submodule_logger in submodule_loggers:
            submodule_logger.propagate = True
               


    @staticmethod
    async def download(track:Track):
        """
            ## ^_^
        """
        return await track.download()

    async def search(self, query: str, limit: int = 1, service: str = "soundcloud",
                     error: bool = True) -> List[Track]:
        """
        Search for tracks across specified music streaming services.

        Parameters:
        -----------
            query (str): The search query.
            limit (int, optional): The maximum number of tracks to return. Default is 1.
            service (str, optional): The music streaming service(s) to search in.
                                    Multiple services can be specified separated by commas.
                                    Default is "soundcloud".
            error (bool, optional): Whether to raise exceptions for errors. Default is True.

        Returns:
        -----------
            List[Track] or Dict[str, List[Track]]: A list of Track objects if only one service is specified,
                                                or a dictionary of lists of Track objects if multiple services are specified.

        Raises:
        -----------
            ServiceUnavailable: If a specified service is unavailable.
            NoResultsFound: If no tracks are found for a specified query.
        """
        
        services = [s.strip() for s in service.split(",") if s.strip()
                    in self.__avaliable_services.keys()]
        self.logger.debug("[SEARCH] New search query: %s. Beginning...", query)
        if len(services) == 1:
            result = []
            services = services[0]
            if not self.services_status[services]:
                if error:
                    self.logger.debug("[SEARCH] Service %s is not available. Not initialized, or initialization error", services)
                    raise ServiceUnavailable(
                        self.__avaliable_services[services])
                else:
                    return []

            service_object = self.services[services]
            tracks = await service_object.search_tracks(query=query, limit=limit)
            if not tracks or len(tracks) == 0:
                if error:
                    raise NoResultsFound(query, self.__avaliable_services[services])
                else:
                    return None

            for track in tracks:
                result.append(TrackFactory.create_track(
                    track, factory=services))

            return result

        elif len(services) > 1:
            if limit == 1:
                return await self.search(
                    query=query,
                    limit=1,
                    service=services[0]
                )

            result = {k: [] for k in services}
            limit_per_service = math.floor(limit / len(services))
            for service in services:
                if not self.services_status[service]:
                    if error:
                        self.logger.debug("[SEARCH] Service %s is not available. Not initialized, or initialization error", services)
                        raise ServiceUnavailable(
                            self.__avaliable_services[service])
                    else:
                        return []

                service_object = self.services[service]
                tracks = await service_object.search_tracks(query=query, limit=limit_per_service)
                if not tracks or len(tracks) == 0:
                    if error:
                        raise NoResultsFound(query, self.__avaliable_services[service])
                    else:
                        return None
                for track in tracks:
                    result[service].append(TrackFactory.create_track(
                        track, factory=service))

            return result
