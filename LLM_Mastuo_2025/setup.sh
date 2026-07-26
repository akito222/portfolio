#!/bin/bash
# 松尾研LLM講座2025 演習ワークスペース セットアップスクリプト
# 使い方: bash setup.sh
set -e

echo "== 1. 仮想環境を作成 =="
python3 -m venv .venv
source .venv/bin/activate

echo "== 2. pipアップグレード =="
pip install --upgrade pip

echo "== 3. PyTorch (CUDA 12.1版) をインストール =="
echo "   ※ GPUがない/対応してない場合は下の行の --index-url 以降を消してください"
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

echo "== 4. その他の依存パッケージをインストール =="
pip install -r requirements.txt

echo "== 5. GPU認識確認 =="
python3 -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"

echo "== セットアップ完了 =="
echo "次回以降は以下で仮想環境に入ってください:"
echo "  source .venv/bin/activate"
