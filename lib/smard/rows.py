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
from typing import Dict, List, Optional, Tuple


def as_instant(timestamp_ms: int) -> datetime.datetime:
    '''
    Converts a SMARD timestamp to an aware datetime

    :param timestamp_ms: Unix timestamp in milliseconds
    :return: the same instant as a timezone aware UTC datetime
    '''
    return datetime.datetime.fromtimestamp(timestamp_ms / 1000, tz=datetime.timezone.utc)


def parse_week(points: List[Tuple[int, Optional[float]]]) -> Dict[datetime.datetime, float]:
    '''
    Keys a week's quarter-hour points by their instant

    A null marks a quarter-hour SMARD has not settled yet; it is dropped here rather than kept as
    None, because it must not be published or move the cursor. Before the market switched to
    quarter-hourly pricing, SMARD repeats the hour's price in all four of its quarter-hours; this
    is passed through unchanged.

    :param points: (timestamp_ms, value in EUR/MWh or None) as delivered by one week's series
    :return: Dict of instant to price in EUR/MWh, settled points only
    '''
    return {as_instant(timestamp_ms): value for timestamp_ms, value in points if value is not None}
