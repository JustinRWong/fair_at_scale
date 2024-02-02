"""
Compute kcore and avg cascade length
Extract the train set for INFECTOR
"""

import json
import math
import os
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict

import numpy as np
import pandas as pd


def remove_duplicates(cascade_nodes, cascade_times):
    """
    Some tweets have more then one retweets from the same person
    Keep only the first retweet of that person
    """
    duplicates = set([x for x in cascade_nodes if cascade_nodes.count(x) > 1])
    for d in duplicates:
        to_remove = [v for v, b in enumerate(cascade_nodes) if b == d][1:]
        cascade_nodes = [b for v, b in enumerate(cascade_nodes) if v not in to_remove]
        cascade_times = [b for v, b in enumerate(cascade_times) if v not in to_remove]

    return cascade_nodes, cascade_times


def get_attribute_dict(fn: str, path: str, attribute: str) -> Dict:
    """
    This function creates a gender dictionary using the profile_gender.csv if the file is available. If the file
    isn't available, it calls the generate_profile_gender_csv() function to generate the CSV and then builds the
    dictionary.

    :param path: path to profile_gender.csv
    :return: gender_dict: dictionary with user IDs as keys and 0 or 1 values indicating that the user is female or male
    """

    try:
        user_profile_df = pd.read_csv(path, encoding="ISO-8859-1")
    except:
        path_user_profile = "weibodata/userProfile/"  ####

        txt_files = [
            os.path.join(path_user_profile, f)
            for f in os.listdir(path_user_profile)
            if os.path.isfile(os.path.join(path_user_profile, f))
        ]
        user_profile_df = pd.concat(
            [pd.read_csv(t, encoding="ISO-8859-1", header=None) for t in txt_files]
        )

        user_profile_df.columns = user_profile_df.iloc[0]
        user_profile_df = user_profile_df[1:]

        uid_map = {uid.strip(): idx for idx, uid in enumerate(user_profile_df[0])}

        if attribute == "gender" and fn == "weibo":
            gender_conversion_dict = {"m": 1, "f": 0}
            user_profile_df[attribute] = user_profile_df[attribute].map(
                gender_conversion_dict
            )

        user_profile_df.to_csv(path, index=False)  # store the processed data

    attribute_dict = pd.Series(
        user_profile_df[attribute].values, index=user_profile_df[0]
    ).to_dict()

    return attribute_dict


def compute_coef(L):
    sigma = np.sqrt(np.mean((L - np.mean(L)) ** 2))  # standard deviation
    coef = sigma / np.mean(L)  # coefficient of variation
    sigmoid = 1 / (1 + np.exp(-coef))
    return 2 * (1 - sigmoid)  # sigmoid function


def compute_fair(node_list, attribute_dict, grouped, attribute="gender"):
    """
    :param node_list: cascade nodes
    :param attribute_dict: original attribute dict
    :param grouped: statistics of attribute dict
    :return: fairness score
    """

    # influenced statistics
    influenced_attribute_dict = {k: attribute_dict[k] for k in node_list}
    T_grouped = defaultdict(list)
    for k, v in influenced_attribute_dict.items():
        T_grouped[v].append(k)

    ratio = [len(T_grouped[k]) / len(grouped[k]) for k in grouped.keys()]

    score = compute_coef(ratio)
    if attribute == "province":
        min_f = 0.00537
        k = 0.566  # coefficient of scaling get from distribution [0.5,1] a=0.5, b=1, k = (b-a)/(max(score)-min(score))
        score = 0.5 + k * (score - min_f)  # 0.5 min scaling border

    return score


def store_samples(
    fn,
    cascade_nodes,
    cascade_times,
    initiators,
    train_set,
    op_time,
    attribute_dict,
    grouped,
    attribute,
    sampling_perc=120,
):
    """
    Store the samples  for the train set as described in the node-context pair creation process for INFECTOR
    """
    # ---- Inverse sampling based on copying time
    no_samples = round(len(cascade_nodes) * sampling_perc / 100)
    casc_len = len(cascade_nodes)
    times = [1.0 / (abs((cascade_times[i] - op_time)) + 1) for i in range(0, casc_len)]
    s_times = sum(times)

    f_score = compute_fair(cascade_nodes, attribute_dict, grouped, attribute)
    if (f_score is not None) and (not np.isnan(f_score)):
        if s_times == 0:
            samples = []
        else:
            probs = [float(i) / s_times for i in times]
            samples = np.random.choice(
                a=cascade_nodes, size=round((no_samples) * f_score), p=probs
            )  # multiplied by fair score for fps
            # samples = np.random.choice(a=cascade_nodes, size=round((no_samples) * f_score), p=probs) # direct sampling for fac
        # ----- Store train set
        op_id = initiators[0]
        for i in samples:
            train_set.write(
                str(op_id) + "," + i + "," + str(casc_len) + "," + str(f_score) + "\n"
            )


def run(fn, attribute, sampling_perc, log):
    print("Reading the network")
    # txt_file_path = '/media/yuting/TOSHIBA EXT/weibo/weibodata/processed4maxmization/weibo/weibo_network.txt' ###
    txt_file_path = "digg/sampled/digg_network_sampled.txt"  ###
    print("Completed reading the network.")

    attribute_csv = "weibodata/processed4maxmization/weibo/profile_gender.csv"  #  !!! use v6  set attribute csv file to write corresponding attribute
    user_attribute_dict = get_attribute_dict(fn, attribute_csv, attribute)

    # group statistics
    attribute_grouped = defaultdict(list)
    for k, v in user_attribute_dict.items():
        attribute_grouped[v].append(k)
    print("generate grouped nodes")

    with open("digg/sampled/train_cascades_sampled.txt", "r") as f, open(
        "train_set_file", "w"
    ) as train_set:
        # ----- Initialize features
        deleted_nodes = []
        log.write(f" net:{fn}\n")
        idx = 0

        start = time.time()
        # ---------------------- Iterate through cascades to create the train set
        for line in f:
            cascade = line.replace("\n", "").split(";")
            if fn == "weibo":
                cascade_nodes = list(map(lambda x: x.split(" ")[0], cascade[1:]))
                cascade_times = list(
                    map(
                        lambda x: int(
                            (
                                (
                                    datetime.strptime(
                                        x.replace("\r", "").split(" ")[1],
                                        "%Y-%m-%d-%H:%M:%S",
                                    )
                                    - datetime.strptime("2011-10-28", "%Y-%m-%d")
                                ).total_seconds()
                            )
                        ),
                        cascade[1:],
                    )
                )
            else:
                cascade_nodes = list(map(lambda x: x.split(" ")[0], cascade))
                cascade_times = list(
                    map(lambda x: int(x.replace("\r", "").split(" ")[1]), cascade)
                )

            # ---- Remove retweets by the same person in one cascade
            cascade_nodes, cascade_times = remove_duplicates(
                cascade_nodes, cascade_times
            )

            # ---------- Dictionary nodes -> cascades
            op_id, op_time = cascade_nodes[0], cascade_times[0]

            if len(cascade_nodes) < 3:
                continue
            initiators = [op_id]

            store_samples(
                fn,
                cascade_nodes[1:],
                cascade_times[1:],
                initiators,
                train_set,
                op_time,
                user_attribute_dict,
                attribute_grouped,
                attribute,
                sampling_perc,
            )

            idx += 1
            if idx % 1000 == 0:
                print("-------------------", idx)

        print(f"Number of nodes not found in the graph: {len(deleted_nodes)}")
    log.write(f"Feature extraction time:{str(time.time() - start)}\n")

    print("Evaluating fairness score of each influencer in train_cascades")

    log.write(f"K-core time:{str(time.time() - start)}\n")
    a = np.array(g.vs["Cumsize_cascades_started"], dtype=np.float)
    b = np.array(g.vs["Cascades_started"], dtype=np.float)

    np.seterr(divide="ignore", invalid="ignore")

    # ------ Store node characteristics
    node_feature_fair_age = "digg/sampled/node_feature_age_fps.csv"
    pd.DataFrame(
        {
            "Node": g.vs["name"],
            "Kcores": kcores,
            "Participated": g.vs["Cascades_participated"],
            "Avg_Cascade_Size": a / b,
        }
    ).to_csv(node_feature_fair_age, index=False)


if __name__ == "__main__":
    with open("time_log.txt", "a") as log:
        input_fn = "weibo"
        sampling_perc = 120
        run(input_fn, "gender", sampling_perc, log)
