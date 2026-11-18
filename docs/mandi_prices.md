# Mandi prices in CropNova

After an assessment, open **Mandi prices**. Select a crop, mandi, variety and grade. The page shows the last imported daily modal price in rupees per quintal and its observation date. Markets come from the selected state, with matches for the chosen district shown first. The forecast section is hidden when there is too little price history.

## Import price data

The source is India's [AGMARKNET variety-wise daily market prices](https://www.data.gov.in/resource/variety-wise-daily-market-prices-data-commodity). For historical experiments, the [yearly Parquet mirror](https://huggingface.co/datasets/DHIVAKARNAIDUSUNKARI/mandi-india-daily-prices-2001-2026) cites the [Manas Khandelwal compilation](https://doi.org/10.34740/kaggle/dsv/15888319) and the original government dataset. Check the date coverage before use. A recent download can still contain old observations.

Download the input files to a local directory. Import them all together to preserve earlier observations when adding a newer file. The importer accepts the fields `State`, `District`, `Market`, `Commodity`, `Variety`, `Grade`, `Arrival_Date` and `Modal_Price`. Prices must be in ₹/quintal.

```sh
python3 scripts/import_mandi_prices.py old-prices.csv new-prices.csv --state Punjab --state Haryana
```

For Parquet files, use an environment with `pyarrow` installed and pass the files to the same command. The application reads `mandi_prices.csv` under `CROPNOVA_DATA_DIR`, or under `instance/` locally. An import replaces the previous CSV atomically. The server picks up the new file automatically. Deployments can mount that directory as a persistent volume. Website requests never download or refresh the source data.

## How the model works

1. Keep each state, district, market, commodity, variety and grade separate. Group observations into Monday–Sunday weeks with at least three reported dates.
2. Use the last three consecutive completed weeks to predict the change in average daily modal price. Compare two small regularised linear regressions with different trend features.
3. Fit on older weeks and choose the feature using later validation weeks. Measure mean absolute error on a separate, newer test block. The baseline simply repeats the previous week's average.
4. Permit a current-week estimate when the chosen regression improves by at least 5%, the three preceding completed weeks qualify and a report is available within seven days. The displayed range uses the historical 80th percentile absolute error. Future errors can exceed that range.
5. Apply rules to explain what the numbers mean. A field mismatch or outstanding check stays visible. For fully matched crops with a qualified forecast, price movement smaller than past forecast error is treated as an unclear signal.

The forecast estimates the average of reported daily modal prices in one calendar week. It supports short-term market comparison. A planting-to-harvest price forecast or a field-yield model would require a separate target, inputs and backtest.
