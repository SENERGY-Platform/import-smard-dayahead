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

import json
import logging
from typing import Callable, List, Optional, Tuple

import requests
from import_lib.import_lib import get_logger

_logger = None


def log() -> logging.Logger:
    # Built on first use: import-lib's logger only carries its static fields after ImportLib() ran init_logging.
    global _logger
    if _logger is None:
        _logger = get_logger(__name__)
    return _logger


BASE_URL = "https://www.smard.de/app/chart_data/"

# 4169 is SMARD's filter id for "Großhandelspreise Day-Ahead", DE its region code for the
# combined Germany/Luxembourg market. Both are fixed properties of the endpoint this import
# reads, not something a deployment configures.
FILTER = "4169"
REGION = "DE"

HTTP_TIMEOUT = 300


def get_bytes(url: str) -> Optional[bytes]:
    '''
    Downloads a URL

    :param url: the URL
    :return: the content, or None if the server did not answer with a success status
    '''
    r = requests.get(url, timeout=HTTP_TIMEOUT)
    if not r.ok:
        return None
    return r.content


def index_url() -> str:
    '''
    :return: URL of the weekly index, one timestamp per week that has a series file
    '''
    return BASE_URL + FILTER + "/" + REGION + "/index_quarterhour.json"


def week_url(timestamp_ms: int) -> str:
    '''
    :param timestamp_ms: a week's timestamp from the index, in Unix milliseconds
    :return: URL of that week's quarter-hour series
    '''
    return BASE_URL + FILTER + "/" + REGION + "/" + FILTER + "_" + REGION + "_quarterhour_" + str(timestamp_ms) \
        + ".json"


def fetch_index(fetch: Callable[[str], Optional[bytes]] = get_bytes) -> List[int]:
    '''
    Downloads the weekly index

    :param fetch: Callable that turns a URL into its content, or None if unavailable
    :return: List of week timestamps in Unix milliseconds, ascending
    :raises Exception: if the index could not be downloaded or parsed
    '''
    url = index_url()
    raw = fetch(url)
    if raw is None:
        raise Exception("Could not get SMARD week index. Network OK?")
    try:
        data = json.loads(raw)
        timestamps = [int(timestamp) for timestamp in data["timestamps"]]
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        raise Exception("Could not parse SMARD week index: " + str(e))
    return sorted(timestamps)


def fetch_week(timestamp_ms: int, fetch: Callable[[str], Optional[bytes]] = get_bytes) \
        -> Optional[List[Tuple[int, Optional[float]]]]:
    '''
    Downloads one week's quarter-hour series

    :param timestamp_ms: the week's timestamp from the index, in Unix milliseconds
    :param fetch: Callable that turns a URL into its content, or None if unavailable
    :return: List of (instant in Unix milliseconds, value in EUR/MWh or None), or None if the week was not
             available or its series could not be parsed
    '''
    url = week_url(timestamp_ms)
    raw = fetch(url)
    if raw is None:
        log().error("No week archive at %s", url)
        return None
    try:
        data = json.loads(raw)
        return [(int(point[0]), point[1]) for point in data["series"]]
    except (json.JSONDecodeError, KeyError, TypeError, ValueError, IndexError) as e:
        log().error("Could not parse week archive at %s: %s", url, e)
        return None
