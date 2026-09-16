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
import json
import unittest
from typing import Dict, List, Optional, Tuple

from lib.smard.api import index_url, week_url
from lib.smard.importer import RECENT_WEEKS, DayAheadImport, as_utc

WEEK_MS = 7 * 24 * 60 * 60 * 1000
QUARTER_MS = 15 * 60 * 1000


def utc(year, month, day, hour=0, minute=0):
    return datetime.datetime(year, month, day, hour, minute, tzinfo=datetime.timezone.utc)


def ms(dt: datetime.datetime) -> int:
    return int(dt.timestamp() * 1000)


WEEK_1 = ms(utc(2024, 8, 26))
WEEK_2 = WEEK_1 + WEEK_MS
WEEK_3 = WEEK_2 + WEEK_MS


class FakeFetcher:
    '''Answers index and week URLs from a Dict, and records every URL it was asked for.'''

    def __init__(self, timestamps: List[int], weeks: Dict[int, List[Tuple[int, Optional[float]]]]):
        self.__archives = {index_url(): json.dumps({"timestamps": timestamps}).encode()}
        for timestamp, points in weeks.items():
            self.__archives[week_url(timestamp)] = json.dumps({"series": points}).encode()
        self.requested: List[str] = []

    def __call__(self, url: str) -> Optional[bytes]:
        self.requested.append(url)
        return self.__archives.get(url)


class RaisingFetcher:
    def __call__(self, url: str) -> Optional[bytes]:
        raise ConnectionError("network down")


class FakeLib:
    '''Stands in for import_lib.ImportLib, recording what would be published.'''

    def __init__(self):
        self.puts: List[Tuple[datetime.datetime, Dict]] = []

    def put(self, date_time: datetime.datetime, value: Dict):
        self.puts.append((date_time, value))


class TestAsUtc(unittest.TestCase):
    def test_a_naive_datetime_is_read_as_utc(self):
        normalised = as_utc(datetime.datetime(2024, 9, 9, 0, 10))
        self.assertEqual(utc(2024, 9, 9, 0, 10), normalised)
        self.assertIsNotNone(normalised.tzinfo)

    def test_an_aware_datetime_keeps_its_instant(self):
        offset = datetime.datetime(2024, 9, 9, 2, 10, tzinfo=datetime.timezone(datetime.timedelta(hours=2)))
        self.assertEqual(utc(2024, 9, 9, 0, 10), as_utc(offset))

    def test_none_stays_none(self):
        self.assertIsNone(as_utc(None))


class TestCursor(unittest.TestCase):
    def test_a_fresh_import_has_no_cursor(self):
        day_ahead_import = DayAheadImport(FakeLib(), "DE/LU", FakeFetcher([], {}))
        day_ahead_import.seed_cursor(None)
        self.assertIsNone(day_ahead_import.cursor())

    def test_seeding_sets_the_cursor(self):
        day_ahead_import = DayAheadImport(FakeLib(), "DE/LU", FakeFetcher([], {}))
        day_ahead_import.seed_cursor(utc(2024, 9, 9, 0, 10))
        self.assertEqual(utc(2024, 9, 9, 0, 10), day_ahead_import.cursor())

    def test_a_naive_signal_is_seeded_as_utc(self):
        day_ahead_import = DayAheadImport(FakeLib(), "DE/LU", FakeFetcher([], {}))
        day_ahead_import.seed_cursor(datetime.datetime(2024, 9, 9, 0, 10))
        self.assertEqual(utc(2024, 9, 9, 0, 10), day_ahead_import.cursor())


class TestImportHistorical(unittest.TestCase):
    def test_publishes_every_settled_point_of_every_week(self):
        fetcher = FakeFetcher(
            [WEEK_1, WEEK_2],
            {
                WEEK_1: [[WEEK_1, 10.0], [WEEK_1 + QUARTER_MS, 11.0]],
                WEEK_2: [[WEEK_2, 20.0], [WEEK_2 + QUARTER_MS, None]],
            },
        )
        lib = FakeLib()
        day_ahead_import = DayAheadImport(lib, "DE/LU", fetcher)
        day_ahead_import.seed_cursor(None)
        count = day_ahead_import.import_historical()
        self.assertEqual(3, count)
        self.assertEqual(
            [utc(2024, 8, 26), utc(2024, 8, 26, 0, 15), utc(2024, 9, 2)],
            [instant for instant, _ in lib.puts],
        )

    def test_advances_the_cursor_to_the_newest_published_instant(self):
        fetcher = FakeFetcher(
            [WEEK_1],
            {WEEK_1: [[WEEK_1, 10.0], [WEEK_1 + QUARTER_MS, 11.0]]},
        )
        day_ahead_import = DayAheadImport(FakeLib(), "DE/LU", fetcher)
        day_ahead_import.seed_cursor(None)
        day_ahead_import.import_historical()
        self.assertEqual(utc(2024, 8, 26, 0, 15), day_ahead_import.cursor())

    def test_a_null_point_is_not_published_and_does_not_advance_the_cursor(self):
        fetcher = FakeFetcher([WEEK_1], {WEEK_1: [[WEEK_1, 10.0], [WEEK_1 + QUARTER_MS, None]]})
        lib = FakeLib()
        day_ahead_import = DayAheadImport(lib, "DE/LU", fetcher)
        day_ahead_import.seed_cursor(None)
        day_ahead_import.import_historical()
        self.assertEqual(1, len(lib.puts))
        self.assertEqual(utc(2024, 8, 26), day_ahead_import.cursor())

    def test_points_at_or_before_the_cursor_are_not_republished(self):
        fetcher = FakeFetcher([WEEK_1], {WEEK_1: [[WEEK_1, 10.0], [WEEK_1 + QUARTER_MS, 11.0]]})
        lib = FakeLib()
        day_ahead_import = DayAheadImport(lib, "DE/LU", fetcher)
        day_ahead_import.seed_cursor(utc(2024, 8, 26))
        count = day_ahead_import.import_historical()
        self.assertEqual(1, count)
        self.assertEqual([utc(2024, 8, 26, 0, 15)], [instant for instant, _ in lib.puts])

    def test_a_missing_week_is_skipped_without_stopping_the_others(self):
        # WEEK_2 is listed in the index but its series file is unavailable.
        fetcher = FakeFetcher([WEEK_1, WEEK_2], {WEEK_1: [[WEEK_1, 10.0]]})
        lib = FakeLib()
        day_ahead_import = DayAheadImport(lib, "DE/LU", fetcher)
        day_ahead_import.seed_cursor(None)
        count = day_ahead_import.import_historical()
        self.assertEqual(1, count)

    def test_the_message_carries_the_configured_market(self):
        fetcher = FakeFetcher([WEEK_1], {WEEK_1: [[WEEK_1, 10.0]]})
        lib = FakeLib()
        day_ahead_import = DayAheadImport(lib, "AT", fetcher)
        day_ahead_import.seed_cursor(None)
        day_ahead_import.import_historical()
        self.assertEqual("AT", lib.puts[0][1]["meta"]["market"])


class TestImportRecent(unittest.TestCase):
    def test_only_reads_the_trailing_recent_weeks_of_the_index(self):
        timestamps = [WEEK_1 + i * WEEK_MS for i in range(RECENT_WEEKS + 2)]
        weeks = {timestamp: [[timestamp, 1.0]] for timestamp in timestamps}
        fetcher = FakeFetcher(timestamps, weeks)
        day_ahead_import = DayAheadImport(FakeLib(), "DE/LU", fetcher)
        day_ahead_import.seed_cursor(None)
        day_ahead_import.import_recent()
        requested_weeks = [url for url in fetcher.requested if url != index_url()]
        self.assertEqual(RECENT_WEEKS, len(requested_weeks))
        for timestamp in timestamps[-RECENT_WEEKS:]:
            self.assertIn(week_url(timestamp), requested_weeks)
        for timestamp in timestamps[:-RECENT_WEEKS]:
            self.assertNotIn(week_url(timestamp), requested_weeks)

    def test_re_reading_an_already_published_week_does_not_republish_it(self):
        fetcher = FakeFetcher([WEEK_1], {WEEK_1: [[WEEK_1, 10.0]]})
        lib = FakeLib()
        day_ahead_import = DayAheadImport(lib, "DE/LU", fetcher)
        day_ahead_import.seed_cursor(None)
        day_ahead_import.import_recent()
        second_count = day_ahead_import.import_recent()
        self.assertEqual(0, second_count)
        self.assertEqual(1, len(lib.puts))

    def test_a_correction_to_an_already_settled_point_is_not_republished(self):
        # SMARD may revise a value it already delivered; the cursor has moved past it and it must
        # not go out a second time, corrected or not.
        fetcher = FakeFetcher([WEEK_1], {WEEK_1: [[WEEK_1, 10.0]]})
        lib = FakeLib()
        day_ahead_import = DayAheadImport(lib, "DE/LU", fetcher)
        day_ahead_import.seed_cursor(utc(2024, 8, 26))
        day_ahead_import.import_recent()
        self.assertEqual(0, len(lib.puts))


class TestImportLatest(unittest.TestCase):
    def test_publishes_like_import_recent(self):
        fetcher = FakeFetcher([WEEK_1], {WEEK_1: [[WEEK_1, 10.0]]})
        lib = FakeLib()
        day_ahead_import = DayAheadImport(lib, "DE/LU", fetcher)
        day_ahead_import.seed_cursor(None)
        count = day_ahead_import.import_latest()
        self.assertEqual(1, count)
        self.assertEqual(utc(2024, 8, 26), day_ahead_import.cursor())

    def test_a_failure_is_caught_and_logged_instead_of_raised(self):
        day_ahead_import = DayAheadImport(FakeLib(), "DE/LU", RaisingFetcher())
        day_ahead_import.seed_cursor(None)
        count = day_ahead_import.import_latest()
        self.assertEqual(0, count)


if __name__ == "__main__":
    unittest.main()
