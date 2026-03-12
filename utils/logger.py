#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""utils/logger.py — KinoProBot uchun Logger"""

import logging
import sys


class Logger:
    """Wrapper class — standart logging ustida"""

    def __init__(self, name: str = "bot"):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%d.%m.%Y %H:%M:%S",
            handlers=[logging.StreamHandler(sys.stdout)],
        )
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("telegram").setLevel(logging.WARNING)
        self.logger = logging.getLogger(name)

    def info(self, msg: str):
        self.logger.info(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def critical(self, msg: str):
        self.logger.critical(msg)

    def debug(self, msg: str):
        self.logger.debug(msg)


# Tayyor logger obyekti
logger = Logger("KinoPro")
