# MermaidSeqBench-Eval

Evaluate LLMs on the [MermaidSeqBench](https://huggingface.co/datasets/ibm-research/MermaidSeqBench) dataset — generation of MermaidJS sequence diagrams from natural language descriptions.

Uses **LLM-as-a-Judge** (GPT-5.1) for scoring across 6 criteria, plus **mmdc render check** for actual syntax validation.

## Tested models

| Model | OpenRouter ID |
|---|---|
| Qwen3-32B | `qwen/qwen3-32b` |
| Kimi K2 | `moonshotai/kimi-k2` |
| GPT-OSS-20B | `openai/gpt-oss-20b` |
| Mixtral 8x22B Instruct | `mistralai/mixtral-8x22b-instruct` |
| GPT-OSS-120B | `openai/gpt-oss-120b` |
| GLM-5 | `z-ai/glm-5` |
| GLM-4.7 | `z-ai/glm-4.7` |
| GLM-4.7-flash | `z-ai/glm-4.7-flash` |

**Judge:** `gpt-5.1` via OpenAI API

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Node.js dependencies (for render check)

```bash
npm install
```

System libraries required for mmdc (Puppeteer/Chrome):

```bash
sudo apt-get install -y libnss3 libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 libasound2t64 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 libcairo2
```

### 3. Configure API keys

```bash
cp .env.example .env
```

Edit `.env` and set:
- `OPENAI_API_KEY` — for GPT-5.1 judge
- `OPEN_ROUTER_API_KEY` — for tested models via OpenRouter

## Usage

### Run the full benchmark

```bash
bash run_benchmark.sh
```

Runs all 8 models sequentially (30 samples each, async with concurrency=5). Results are saved to `./results/<model_name>/`.

### Run a single model

```bash
python3 eval.py \
  --model qwen/qwen3-32b \
  --model_api_endpoint https://openrouter.ai/api/v1 \
  --model_api_key OPEN_ROUTER_API_KEY \
  --judge gpt-5.1 \
  --judge_api_endpoint https://api.openai.com/v1 \
  --judge_api_key OPENAI_API_KEY \
  --limit 30 \
  --output ./results/qwen3-32b
```

### Build summary report

```bash
python3 build_summary.py
```

Generates `results/summary.xlsx` with:
- Mean scores per model across all 6 judge criteria
- Render rate (% of diagrams that successfully render via mmdc)
- Legend with column descriptions

### Explore results interactively

Open `results/analysis.ipynb` — charts, radar diagrams, per-row scores, worst cases.

## Evaluation criteria (LLM-as-a-Judge)

| Criterion | Description |
|---|---|
| `syntax` | MermaidJS syntax correctness: participant declarations, activate/deactivate balance, alt/else/end blocks |
| `mermaid_only` | Output contains only MermaidJS code, no extra text or explanations |
| `logic` | Logic and flow completeness: every request has a response, alternate branches covered |
| `completeness` | Full coverage of all participants, request/response pairs, and decision points |
| `activation_handling` | Correct use of activate/deactivate: balanced, no unnecessary deactivations |
| `error_and_status_tracking` | Error handling and status tracking: clear success/failure flow separation |
| `render_rate` | Fraction of diagrams that successfully render via `mmdc` (Mermaid CLI) |

## CLI arguments (eval.py)

| Argument | Default | Description |
|---|---|---|
| `--model` | required | Model ID (e.g. `qwen/qwen3-32b`) |
| `--model_api_endpoint` | required | API endpoint URL |
| `--model_api_key` | `OPENAI_API_KEY` | Env variable name for model API key |
| `--judge` | required | Judge model ID |
| `--judge_api_endpoint` | required | Judge API endpoint URL |
| `--judge_api_key` | `OPENAI_API_KEY` | Env variable name for judge API key |
| `--limit` | no limit | Limit dataset to first N rows |
| `--concurrency` | 5 | Max parallel API requests |
| `--output` | `./` | Output directory |
| `--crit_file` | `judge-criteria.yaml` | Path to judge criteria YAML |

## Citation

```bibtex
@misc{shbita2025mermaidseqbenchevaluationbenchmarkllmtomermaid,
      title={MermaidSeqBench: An Evaluation Benchmark for LLM-to-Mermaid Sequence Diagram Generation},
      author={Basel Shbita and Farhan Ahmed and Chad DeLuca},
      year={2025},
      eprint={2511.14967},
      archivePrefix={arXiv},
      primaryClass={cs.SE},
      url={https://arxiv.org/abs/2511.14967},
}
```
