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

from lib.smard.messages import UNITS, build_message


class TestBuildMessage(unittest.TestCase):
    def test_carries_the_price(self):
        message = build_message(45.2, "DE/LU")
        self.assertAlmostEqual(45.2, message["price_eur_mwh"], places=9)

    def test_carries_the_market_from_configuration(self):
        message = build_message(45.2, "DE/LU")
        self.assertEqual("DE/LU", message["meta"]["market"])

    def test_a_different_market_label_is_carried_unchanged(self):
        self.assertEqual("AT", build_message(45.2, "AT")["meta"]["market"])

    def test_carries_the_units(self):
        self.assertEqual(UNITS, build_message(45.2, "DE/LU")["meta"]["units"])

    def test_the_message_is_json_serialisable(self):
        json.loads(json.dumps(build_message(45.2, "DE/LU")))

    def test_the_units_are_not_shared_between_messages(self):
        first = build_message(45.2, "DE/LU")
        first["meta"]["units"]["price_eur_mwh"] = "changed"
        self.assertEqual("EUR/MWh", build_message(45.2, "DE/LU")["meta"]["units"]["price_eur_mwh"])

    def test_a_negative_price_is_carried_unchanged(self):
        # Day-ahead prices go negative during oversupply; that is a real price, not a marker.
        self.assertAlmostEqual(-12.5, build_message(-12.5, "DE/LU")["price_eur_mwh"], places=9)


if __name__ == "__main__":
    unittest.main()
