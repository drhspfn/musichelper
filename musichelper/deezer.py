from musichelper.util import Parameters, SingletonMeta, setup_logger
from asyncio import AbstractEventLoop
from logging import Logger, DEBUG, INFO


class Deezer(metaclass=SingletonMeta):
    def __init__(self, arl: str, loop: AbstractEventLoop) -> None:
        self.__arl: str = arl
        self.__loop = loop
        self.cookies = {'arl': self.__arl}
        self.is_debug = Parameters().get_instance().debug
        self.logger: Logger = setup_logger(
            "musichelper.deezer", level=DEBUG if self.is_debug else INFO)
        self.logger.info("Deezer initialized")

    def debug(self, msg: str, *args: object):
        if self.is_debug:
            self.logger.debug(msg, *args)