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
import unittest
from typing import Optional

from lib.smard.api import fetch_index, fetch_week, index_url, week_url

ARCHIVES = {
    index_url(): json.dumps({"timestamps": [1725926400000, 1725321600000, 1726531200000]}).encode(),
    week_url(1725321600000): json.dumps({"series": [[1725321600000, 45.2], [1725322500000, None]]}).encode(),
}


def stub_fetch(url: str) -> Optional[bytes]:
    return ARCHIVES.get(url)


class TestIndexUrl(unittest.TestCase):
    def test_builds_the_quarterhour_index_url_for_filter_4169_region_de(self):
        self.assertEqual(
            "https://www.smard.de/app/chart_data/4169/DE/index_quarterhour.json",
            index_url(),
        )


class TestWeekUrl(unittest.TestCase):
    def test_builds_the_week_url_with_its_timestamp(self):
        self.assertEqual(
            "https://www.smard.de/app/chart_data/4169/DE/4169_DE_quarterhour_1725321600000.json",
            week_url(1725321600000),
        )


class TestFetchIndex(unittest.TestCase):
    def test_returns_the_timestamps_sorted_ascending(self):
        self.assertEqual([1725321600000, 1725926400000, 1726531200000], fetch_index(stub_fetch))

    def test_raises_when_the_index_is_unavailable(self):
        with self.assertRaises(Exception):
            fetch_index(lambda url: None)

    def test_raises_on_malformed_json(self):
        with self.assertRaises(Exception):
            fetch_index(lambda url: b"not json")

    def test_raises_when_the_timestamps_field_is_missing(self):
        with self.assertRaises(Exception):
            fetch_index(lambda url: b"{}")


class TestFetchWeek(unittest.TestCase):
    def test_returns_the_points_of_the_week(self):
        self.assertEqual(
            [(1725321600000, 45.2), (1725322500000, None)],
            fetch_week(1725321600000, stub_fetch),
        )

    def test_returns_none_when_the_week_is_unavailable(self):
        self.assertIsNone(fetch_week(1725321600000, lambda url: None))

    def test_returns_none_on_malformed_json(self):
        self.assertIsNone(fetch_week(1725321600000, lambda url: b"not json"))

    def test_returns_none_when_the_series_field_is_missing(self):
        self.assertIsNone(fetch_week(1725321600000, lambda url: b"{}"))


if __name__ == "__main__":
    unittest.main()
