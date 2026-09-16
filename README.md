# import-smard-dayahead

Imports the day-ahead wholesale electricity prices for the German/Luxembourg market at quarter-hour
resolution. If configured, historic and recent weeks are imported first. Afterwards, the latest data is
checked every hour, which matches the auction's own cadence of one publication per day.

The event time handed to the platform is the UTC instant of the quarter-hour. Before the market switched to
quarter-hourly pricing, SMARD repeats the hour's price in all four of its quarter-hours; this import passes
that through unchanged rather than interpolating or deduplicating it.

## Outputs
* price_eur_mwh (float): the day-ahead price (EUR/MWh)
* meta (Object):
  + market (string): the market region label, from configuration
  + units (Object): the unit of every value above, by name

A quarter-hour SMARD has not settled yet is delivered as `null` and is not published: publishing it would
move the cursor past an instant that later carries a real price.

## Configs
* HISTORIC (bool): If true, all available historic weeks are imported once at startup. Default: false
* RECENT (bool): If true and HISTORIC did not just run, the most recent weeks are imported once at
  startup. Skipped when HISTORIC ran, because the historical import already reads those same weeks as
  part of the full index. Default: true
* MARKET (string): Label attached to every message as `meta.market`. Purely descriptive: it does not change
  which data is fetched, the import always reads SMARD's German/Luxembourg day-ahead auction (filter 4169,
  region DE). Default: "DE/LU"

A quarter-hour is published only once and the cursor never goes back, so a price SMARD later corrects is not
republished under the corrected value. RECENT and the hourly schedule both reread the last few weeks of the
index rather than just the newest one, because SMARD occasionally corrects a week after it first published
it; rereading only the newest week would miss a correction landing in the week before it. How many weeks are
reread is `RECENT_WEEKS` in `lib/smard/importer.py`.

---

This tool uses publicly available data provided by Bundesnetzagentur (SMARD).
