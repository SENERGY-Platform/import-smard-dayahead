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

import time

import schedule
from import_lib.import_lib import ImportLib, get_logger

from lib.smard.importer import DayAheadImport, as_utc

if __name__ == '__main__':
    lib = ImportLib("github.com/SENERGY-Platform/import-smard-dayahead")
    logger = get_logger(__name__)

    market = lib.get_config("MARKET", "DE/LU")

    last_published, _ = lib.get_last_published_datetime()
    last_published = as_utc(last_published)
    if last_published is None:
        logger.info("Import is starting fresh")
    else:
        logger.info("Import is continuing previous import at %s", last_published)

    day_ahead_import = DayAheadImport(lib, market)
    day_ahead_import.seed_cursor(last_published)

    if lib.get_config("HISTORIC", False):
        logger.info("Importing historic data...")
        day_ahead_import.import_historical()
    elif lib.get_config("RECENT", True):
        # The historical import already reads the full index, including the weeks a recent
        # import would reread, so running both on the same startup would fetch them twice.
        logger.info("Importing recent data...")
        day_ahead_import.import_recent()
    else:
        logger.info("Skipping historic and recent data (not configured)")

    day_ahead_import.import_latest()

    logger.info("Setting schedule to run every hour")
    schedule.every(1).hours.do(day_ahead_import.import_latest)

    while True:
        schedule.run_pending()
        time.sleep(1)
