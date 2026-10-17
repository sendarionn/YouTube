"""学歴調査用の無作為標本を作る

公開情報で学歴が分かる人だけを集計すると、有名な創業者に偏る
そこで創業20年以内の対象企業の創業者（氏名判明）から無作為に抽出し、標本内の判明率を上げて集計する
使い方: python edu_sample.py [標本数]
出力: data/edu_sample.csv
"""
import sys

import pandas as pd

from paths import DATA

SEED = 20261017


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    f = pd.read_csv(DATA / "founders.csv", dtype=str).fillna("")
    pool = f[(f.target_20y == "Y") & (f.name != "")]
    s = pool.sample(n=n, random_state=SEED).sort_values("founder_id")
    s[["founder_id", "name", "company", "origin_ym", "birth_year", "education_raw"]].to_csv(DATA / "edu_sample.csv", index=False)
    print(len(pool), "人から", len(s), "人を抽出")


if __name__ == "__main__":
    main()
