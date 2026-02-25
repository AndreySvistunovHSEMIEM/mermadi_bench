#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LIMIT=30
JUDGE="gpt-5.1"
JUDGE_ENDPOINT="https://api.openai.com/v1"
MODEL_ENDPOINT="https://openrouter.ai/api/v1"

MODELS=(
    "qwen/qwen3-32b"
    "moonshotai/kimi-k2"
    "openai/gpt-oss-20b"
    "mistralai/mixtral-8x22b-instruct"
    "openai/gpt-oss-120b"
    "z-ai/glm-5"
    "z-ai/glm-4.7"
    "z-ai/glm-4.7-flash"
)

for MODEL in "${MODELS[@]}"; do
    # e.g. "qwen/qwen3-32b" -> "qwen3-32b"
    MODEL_NAME="${MODEL##*/}"
    OUTPUT_DIR="./results/${MODEL_NAME}"

    echo "========================================"
    echo "Running model: ${MODEL}"
    echo "Output:        ${OUTPUT_DIR}"
    echo "========================================"

    python3 eval.py \
        --model "$MODEL" \
        --model_api_endpoint "$MODEL_ENDPOINT" \
        --model_api_key OPEN_ROUTER_API_KEY \
        --judge "$JUDGE" \
        --judge_api_endpoint "$JUDGE_ENDPOINT" \
        --judge_api_key OPENAI_API_KEY \
        --limit "$LIMIT" \
        --output "$OUTPUT_DIR"

    echo ""
done

echo "All models completed."
