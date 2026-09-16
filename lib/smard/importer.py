# Copyright 2026 InfAI (CC SES)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import logging
from typing import Callable, Dict, List, Optional

from import_lib.import_lib import get_logger

from lib.smard.api import fetch_index, fetch_week, get_bytes
from lib.smard.messages import build_message
from lib.smard.rows import parse_week

_logger = None

# How many trailing weeks of the index a "recent" or scheduled run rereads. SMARD occasionally
# corrects quarter-hours it already published, so rereading only the newest week would miss a
# correction landing in the week before it.
RECENT_WEEKS = 4


def log() -> logging.Logger:
    # Built on first use: import-lib's logger only carries its static fields after ImportLib() ran init_logging.
    global _logger
    if _logger is None:
        _logger = get_logger(__name__)
    return _logger


def as_utc(value: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
    '''
    Normalises a datetime to timezone aware UTC

    import_lib returns the last published timestamp without a timezone even though it published it as UTC;
    comparing that against an aware datetime would raise.

    :param value: a datetime or None
    :return: the same instant as an aware UTC datetime, or None
    '''
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)
    return value.astimezone(datetime.timezone.utc)


class DayAheadImport:
    '''
    Publishes the day-ahead quarter-hour prices of one market, tracked by a single cursor
    '''

    def __init__(self, lib, market: str, fetch: Callable[[str], Optional[bytes]] = get_bytes):
        self.__lib = lib
        self.__market = market
        self.__fetch = fetch
        self.__cursor: Optional[datetime.datetime] = None

    def seed_cursor(self, last_published: Optional[datetime.datetime]) -> None:
        '''
        Sets the cursor to the last published instant

        :param last_published: last published instant, aware UTC, or None for a fresh import
        :return: None
        '''
        self.__cursor = as_utc(last_published)

    def cursor(self) -> Optional[datetime.datetime]:
        '''
        :return: the newest instant published so far, or None if nothing was published yet
        '''
        return self.__cursor

    def import_historical(self) -> int:
        '''
        Publishes every settled quarter-hour of the full week index that is newer than the cursor

        :return: number of published data points
        '''
        timestamps = fetch_index(self.__fetch)
        count = self.__import_weeks(timestamps)
        log().info("Imported %s historical data points", count)
        return count

    def import_recent(self) -> int:
        '''
        Publishes the settled quarter-hours of the last RECENT_WEEKS index entries that are newer than the cursor

        :return: number of published data points
        '''
        timestamps = fetch_index(self.__fetch)
        count = self.__import_weeks(timestamps[-RECENT_WEEKS:])
        log().info("Imported %s recent data points", count)
        return count

    def import_latest(self) -> int:
        '''
        Publishes what is new since the last run. Errors are caught and logged rather than raised, so a failing
        run does not break the schedule loop it runs in.

        :return: number of published data points, 0 on error
        '''
        try:
            timestamps = fetch_index(self.__fetch)
            count = self.__import_weeks(timestamps[-RECENT_WEEKS:])
            log().info("Imported %s latest data points", count)
            return count
        except Exception as e:
            log().error("Could not import latest data: %s", e)
            return 0

    def __import_weeks(self, timestamps: List[int]) -> int:
        count = 0
        # Ascending, as the index already is, so the cursor only ever moves forward.
        for timestamp in timestamps:
            points = fetch_week(timestamp, self.__fetch)
            if points is None:
                continue
            count += self.__publish(parse_week(points))
        return count

    def __publish(self, prices: Dict[datetime.datetime, float]) -> int:
        count = 0
        cursor = self.__cursor
        debug = log().isEnabledFor(logging.DEBUG)
        for instant in sorted(prices):
            if cursor is not None and instant <= cursor:
                continue
            value = build_message(prices[instant], self.__market)
            if debug:
                log().debug("%s: %s", instant, value)
            self.__lib.put(instant, value)
            cursor = instant
            self.__cursor = cursor
            count += 1
        return count
