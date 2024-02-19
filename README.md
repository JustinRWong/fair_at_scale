# Influence Maximization Documentation

- Author: Justin Wong <justinryanwong@berkeley.edu>

# [soc-digg](https://networkrepository.com/soc-digg.php) dataset

After downloading and unzipping the data set, place the soc-digg folder into the `Data` folder. The path should include

```
# Data Directory Structure

The `Data` directory should have the following structure:

- `Soc-digg/`
  - `output/`
    - `wc_soc-digg_network.csv`
  - `soc-digg.mtx`

Make sure to place the `soc-digg` folder into the `Data` directory after downloading and unzipping the dataset.

```

## To run the preprocess for imm script:

```
cd models
python3 preprocess_for_imm.py --fn soc-digg --source-network Data/soc-digg/soc-digg.mtx
```

This will generate the following files:

## Generated Files

After running the `preprocess_for_imm.py` script, the following files will be generated:

- `Data/soc-digg/output/wc_soc-digg_network.csv`: CSV file containing the weighted cascade network data.
- `Data/soc-digg/output/soc-digg_incr_dic.json`: JSON file mapping incremental node ids for IMM.
- `Data/soc-digg/output/wc_soc-digg_attribute.txt`: Text file containing attributes for the network.

Additionally, a log file will be created in the `logs` directory with the format `preprocess_for_imm-<timestamp>.log`.
