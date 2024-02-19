"""
Weigh all networks based on weighted cascade, and derive the attribute file required for IMM
"""

import argparse
import json
import logging
import os
import time

import pandas as pd

# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
# formatter = logging.Formatter(
#     '%(asctime)s | %(name)s |  %(levelname)s: %(message)s')
LOG_FN = f"preprocess_for_imm-{time.time()}.log"
logging.basicConfig(
    filename=f"logs/{LOG_FN}",
    filemode="a",
    format="%(asctime)s | %(name)s |  %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    level=logging.DEBUG,
)
LOGGER_INSTANCE = logging.getLogger("PreprocessForIMM")


def setup_directories(dir):
    if not os.path.exists(dir):
        LOGGER_INSTANCE.debug(f"Creating the nonexistent folder: {dir}")
        os.makedirs(dir)
    else:
        LOGGER_INSTANCE.debug(f"Folder already exists: {dir}")


def run(fn, source_network):
    start = time.time()
    base_dir = "Data/" + fn.capitalize()
    output_dir = f"{base_dir}/output"
    setup_directories(base_dir)
    setup_directories(output_dir)
    LOGGER_INSTANCE.debug(f"base_dir: {base_dir}")
    LOGGER_INSTANCE.debug(f"output_dir: {output_dir}")

    base_dir_and_partial_filename = f"{base_dir}/output/wc_{fn}"
    # --- Read graph
    with open(
        f"{base_dir_and_partial_filename}_attribute.txt", "w", encoding="utf-8"
    ) as attribute_file:
        graph = pd.read_csv(
            source_network,
            sep=" ",
            header=1,
            skiprows=2,  # 2 for the soc-digg dataset
            # fn.capitalize() + "/Init_Data/" + fn + "_network.txt", sep=" "
        )
        LOGGER_INSTANCE.info(f"Loaded pd dataframe from: {source_network}")
        if graph.shape[1] > 2:
            graph = graph.drop(graph.columns[2], 1)
        graph.columns = ["node1", "node2"]

        LOGGER_INSTANCE.info("Creating graph...")
        # --- Compute influence weight
        outdegree = graph.groupby("node1").agg("count").reset_index()
        LOGGER_INSTANCE.debug(f"Initial Outdegree head: {outdegree.head()}")

        outdegree.columns = ["node1", "outdegree"]

        outdegree["outdegree"] = 1 / outdegree["outdegree"]
        outdegree["outdegree"] = outdegree["outdegree"].apply(
            lambda x: float("%s" % float("%.6f" % x))
        )

        LOGGER_INSTANCE.debug(f"Processed Outdegree head: {outdegree.head()}")

        # --- Assign it
        graph = graph.merge(outdegree, on="node1")

        # --- Find all nodes to create incremental ids for IMM
        all_nodes = list(
            set(graph["node1"].unique()).union(set(graph["node2"].unique()))
        )

        dic = {int(all_nodes[i]): i for i in range(0, len(all_nodes))}
        graph["node1"] = graph["node1"].map(dic)
        graph["node2"] = graph["node2"].map(dic)

        LOGGER_INSTANCE.debug(f"Fully created graph with {len(all_nodes)} nodes")
        # --- Store the ids to translate the seeds_result of IMM
        with open(
            f"{base_dir}/output/{fn}_incr_dic.json", "w", encoding="utf-8"
        ) as json_file:
            json.dump(dic, json_file)

        # --- Store
        graph = graph[["node2", "node1", "outdegree"]]
        output_graph_csv_fn = f"{base_dir_and_partial_filename}_network.csv"
        graph.to_csv(
            output_graph_csv_fn,
            header=False,
            index=False,
            sep=" ",
        )
        LOGGER_INSTANCE.debug(f"Dumped graph to csv file: {output_graph_csv_fn}")
        LOGGER_INSTANCE.info(f"Time for wc {fn} network:{str(time.time() - start)}\n")

        attribute_file.write(f"n={str(len(all_nodes) + 1)}\n")
        attribute_file.write(f"m={str(graph.shape[0])}\n")


def main():
    parser = argparse.ArgumentParser(description="Preprocess for IMM")
    parser.add_argument("--fn", type=str, help="File name")
    parser.add_argument("--source-network", type=str, help="Path to attribute CSV file")
    args = parser.parse_args()

    fn = args.fn
    source_network = args.source_network
    if not os.path.exists("logs"):
        os.makedirs("logs")
    # log = open(f"logs/{time.time()}preprocess_log.txt", "w", encoding="utf-8")
    run(fn, source_network)
    # log.close()


if __name__ == "__main__":
    main()
