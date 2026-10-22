#!/bin/bash
# 学習用データの前処理（webui.py の open1abc と同じ手順を CPU で実行する）
set -e
cd "$(dirname "$0")/.."
export inp_text="$1" inp_wav_dir="" exp_name=self opt_dir=logs/self is_half=False i_part=0 all_parts=1 \
  version=v2ProPlus bert_pretrained_dir=GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large \
  cnhubert_base_dir=GPT_SoVITS/pretrained_models/chinese-hubert-base \
  sv_path=GPT_SoVITS/pretrained_models/sv/pretrained_eres2netv2w24s4ep4.ckpt \
  pretrained_s2G=GPT_SoVITS/pretrained_models/v2Pro/s2Gv2ProPlus.pth s2config_path=GPT_SoVITS/configs/s2v2ProPlus.json
export PYTHONPATH="$PWD:$PWD/GPT_SoVITS"
mkdir -p logs/self
PY=.venv/bin/python
$PY -s GPT_SoVITS/prepare_datasets/1-get-text.py
mv logs/self/2-name2text-0.txt logs/self/2-name2text.txt
$PY -s GPT_SoVITS/prepare_datasets/2-get-hubert-wav32k.py
$PY -s GPT_SoVITS/prepare_datasets/2-get-sv.py
$PY -s GPT_SoVITS/prepare_datasets/3-get-semantic.py
{ echo -e "item_name\tsemantic_audio"; cat logs/self/6-name2semantic-0.tsv; } > logs/self/6-name2semantic.tsv
rm logs/self/6-name2semantic-0.tsv
echo PREPARE_DONE
