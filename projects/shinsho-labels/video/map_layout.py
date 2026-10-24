"""レーベルの地図の配置：分野の構成の距離（ジェンセン・シャノン距離）を2次元に置く

入力：research/data/ndc_distance.csv（2016〜2025年に20点以上の67シリーズ）
出力：video/map_layout.json（座標と、2次元にしたことによる歪みの指標）
方法
- 古典的多次元尺度構成法（MDS）で初期配置を作り、SMACOF（ストレスを下げる反復）で整える。乱数を使わないため毎回同じ配置
- 歪みの指標：ストレス1（0 に近いほど元の距離を保つ）、元の距離と図上の距離の順位相関、
  各シリーズの最も近いシリーズが図上でも最も近い割合
- 図上の距離は元の距離の近似。動画では「近い・遠い」の目安として示し、距離の値は図から読ませない
"""
import csv
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "research" / "data"


def load():
    rows = list(csv.DictReader((DATA / "ndc_distance.csv").open(encoding="utf-8")))
    labels = sorted({r["label_a"] for r in rows} | {r["label_b"] for r in rows})
    idx = {l: i for i, l in enumerate(labels)}
    D = np.zeros((len(labels), len(labels)))
    for r in rows:
        i, j = idx[r["label_a"]], idx[r["label_b"]]
        D[i, j] = D[j, i] = float(r["jsd"])
    return labels, D


def classical(D, k=2):
    n = len(D)
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ (D ** 2) @ J
    w, v = np.linalg.eigh(B)
    order = np.argsort(w)[::-1][:k]
    return v[:, order] * np.sqrt(np.maximum(w[order], 0))


def smacof(D, X, iters=500):
    n = len(D)
    for _ in range(iters):
        d = np.sqrt(((X[:, None] - X[None]) ** 2).sum(-1))
        np.fill_diagonal(d, 1)
        B = -D / d
        np.fill_diagonal(B, 0)
        np.fill_diagonal(B, -B.sum(1))
        X = B @ X / n
    return X


def rank(a):
    r = np.empty(len(a))
    r[np.argsort(a)] = np.arange(len(a))
    return r


def main():
    labels, D = load()
    X = smacof(D, classical(D))
    # 向きをそろえる：自然科学に特化したブルーバックスを右にする（回転・反転は距離を変えない）
    X -= X.mean(0)
    if X[labels.index("ブルーバックス"), 0] < 0:
        X[:, 0] *= -1
    if X[labels.index("交通新聞社新書"), 1] > 0:
        X[:, 1] *= -1
    d = np.sqrt(((X[:, None] - X[None]) ** 2).sum(-1))
    iu = np.triu_indices(len(D), 1)
    stress = float(np.sqrt(((D[iu] - d[iu]) ** 2).sum() / (D[iu] ** 2).sum()))
    rho = float(np.corrcoef(rank(D[iu]), rank(d[iu]))[0, 1])
    nn = np.mean([np.argsort(np.where(np.arange(len(D)) == i, 9, D[i]))[0] ==
                  np.argsort(np.where(np.arange(len(D)) == i, 9, d[i]))[0] for i in range(len(D))])
    out = {"labels": labels, "xy": X.round(4).tolist(),
           "distortion": {"stress1": round(stress, 3), "spearman": round(rho, 3), "nearest_kept": round(float(nn), 3),
                          "n_labels": len(labels), "n_pairs": int(len(iu[0]))}}
    (HERE / "map_layout.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out["distortion"])


if __name__ == "__main__":
    main()
