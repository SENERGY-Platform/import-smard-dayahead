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
import unittest

from lib.smard.rows import as_instant, parse_week


def utc(year, month, day, hour, minute):
    return datetime.datetime(year, month, day, hour, minute, tzinfo=datetime.timezone.utc)


class TestAsInstant(unittest.TestCase):
    def test_converts_unix_milliseconds_to_aware_utc(self):
        # 2024-09-09T12:00:00Z
        instant = as_instant(1725883200000)
        self.assertEqual(utc(2024, 9, 9, 12, 0), instant)
        self.assertIsNotNone(instant.tzinfo)


class TestParseWeek(unittest.TestCase):
    def test_keys_points_by_their_instant(self):
        points = [(1725883200000, 45.2), (1725884100000, 46.8)]
        parsed = parse_week(points)
        self.assertEqual(45.2, parsed[utc(2024, 9, 9, 12, 0)])
        self.assertEqual(46.8, parsed[utc(2024, 9, 9, 12, 15)])

    def test_drops_points_that_are_not_settled_yet(self):
        points = [(1725883200000, 45.2), (1725884100000, None)]
        parsed = parse_week(points)
        self.assertEqual([utc(2024, 9, 9, 12, 0)], list(parsed))

    def test_an_empty_week_parses_to_an_empty_dict(self):
        self.assertEqual({}, parse_week([]))

    def test_a_week_of_nothing_but_nulls_parses_to_an_empty_dict(self):
        self.assertEqual({}, parse_week([(1725883200000, None), (1725884100000, None)]))

    def test_repeated_hourly_values_before_the_market_switch_pass_through_unchanged(self):
        # Pre-switchover, all four quarter-hours of an hour carry the same price.
        points = [
            (1725883200000, 45.2),
            (1725884100000, 45.2),
            (1725885000000, 45.2),
            (1725885900000, 45.2),
        ]
        parsed = parse_week(points)
        self.assertEqual(4, len(parsed))
        self.assertTrue(all(value == 45.2 for value in parsed.values()))


if __name__ == "__main__":
    unittest.main()
