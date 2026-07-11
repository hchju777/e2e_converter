#!/bin/bash
# 개발 환경 실행 스크립트

cd "$(dirname "$0")/.."

# 가상환경 활성화 (Linux/Mac)
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "[ERROR] Virtual environment not found. Run: python -m venv .venv"
    exit 1
fi

# 웹 앱 실행
python main.py web
