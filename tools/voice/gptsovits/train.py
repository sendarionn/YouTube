"""追加学習（webui.py の open1Ba と open1Bb と同じ設定を、CPU・32ビットで作って実行する）

使い方（models/gpt-sovits で）：.venv/bin/python local/train.py [sovits|gpt|all] [SoVITS のエポック数] [GPT のエポック数]
出力：SoVITS_weights_v2ProPlus/self_e*_s*.pth、GPT_weights_v2ProPlus/self-e*.ckpt
"""
import json
import os
import subprocess
import sys

import yaml

VERSION = "v2ProPlus"
EXP = "self"
EXP_DIR = f"logs/{EXP}"
PY = ".venv/bin/python"
ENV = {**os.environ, "NUM_WORKERS": "0", "PYTHONPATH": f"{os.getcwd()}:{os.getcwd()}/GPT_SoVITS", "version": VERSION, "hz": "25hz",
       "_CUDA_VISIBLE_DEVICES": "0"}


def sovits(epochs, batch_size=4):
    with open(f"GPT_SoVITS/configs/s2{VERSION}.json") as f:
        data = json.load(f)
    data["train"].update(fp16_run=False, batch_size=batch_size, epochs=epochs, text_low_lr_rate=0.4,
                         pretrained_s2G=f"GPT_SoVITS/pretrained_models/v2Pro/s2G{VERSION}.pth",
                         pretrained_s2D=f"GPT_SoVITS/pretrained_models/v2Pro/s2D{VERSION}.pth",
                         if_save_latest=True, if_save_every_weights=True, save_every_epoch=epochs,
                         gpu_numbers="0", grad_ckpt=False, lora_rank=32)
    data["model"]["version"] = VERSION
    data["data"]["exp_dir"] = data["s2_ckpt_dir"] = EXP_DIR
    data["save_weight_dir"] = f"SoVITS_weights_{VERSION}"
    data["name"] = EXP
    data["version"] = VERSION
    os.makedirs(f"{EXP_DIR}/logs_s2_{VERSION}", exist_ok=True)
    os.makedirs(data["save_weight_dir"], exist_ok=True)
    path = f"{EXP_DIR}/tmp_s2.json"
    with open(path, "w") as f:
        json.dump(data, f)
    subprocess.run([PY, "-s", "GPT_SoVITS/s2_train.py", "--config", path], env=ENV, check=True)


def gpt(epochs, batch_size=4):
    with open("GPT_SoVITS/configs/s1longer-v2.yaml") as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    data["train"].update(precision="32", batch_size=batch_size, epochs=epochs, save_every_n_epoch=epochs,
                         if_save_every_weights=True, if_save_latest=True, if_dpo=False,
                         half_weights_save_dir=f"GPT_weights_{VERSION}", exp_name=EXP)
    data["data"]["num_workers"] = 0
    data["pretrained_s1"] = "GPT_SoVITS/pretrained_models/s1v3.ckpt"
    data["train_semantic_path"] = f"{EXP_DIR}/6-name2semantic.tsv"
    data["train_phoneme_path"] = f"{EXP_DIR}/2-name2text.txt"
    data["output_dir"] = f"{EXP_DIR}/logs_s1_{VERSION}"
    os.makedirs(f"GPT_weights_{VERSION}", exist_ok=True)
    path = f"{EXP_DIR}/tmp_s1.yaml"
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
    subprocess.run([PY, "-s", "GPT_SoVITS/s1_train.py", "--config_file", path], env=ENV, check=True)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    e2 = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    e1 = int(sys.argv[3]) if len(sys.argv) > 3 else 15
    if what in ("sovits", "all"):
        sovits(e2)
    if what in ("gpt", "all"):
        gpt(e1)
    print("TRAIN_DONE")
