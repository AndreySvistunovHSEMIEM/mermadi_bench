import asyncio
import pandas as pd
import argparse
import yaml
from datasets import load_dataset, Dataset
from openai import AsyncOpenAI
from utils import *


log = get_logger(__name__)


# -------- LLM helpers --------


async def generate_one(sem, client, model, user_prompt, idx):
    async with sem:
        log.debug(f"[model] user_prompt: {user_prompt}")
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": str(user_prompt)}],
                max_completion_tokens=DEFAULT_MAX_NEW_TOKENS_MODEL,
                temperature=0,
            )
            return idx, response.choices[0].message.content
        except Exception as e:
            log.debug(f"[model] Error from API: {e}")
            return idx, ''


async def evaluate_one(sem, judge_client, judge_model, prompt_template,
                       agent_prompt, agent_response, expected_agent_response, idx):
    async with sem:
        context = {
            "agent_prompt": agent_prompt,
            "agent_response": agent_response,
            "expected_agent_response": expected_agent_response
        }
        rendered_prompt = render_prompt(prompt_template, context)
        log.debug(f'[evaluate] rendered_prompt: {rendered_prompt}')
        response = await judge_client.chat.completions.create(
            model=judge_model,
            messages=[
                {"role": "system", "content": str(JUDGE_SYS_PROMPT)},
                {"role": "user", "content": str(rendered_prompt)}
            ],
            max_completion_tokens=DEFAULT_MAX_NEW_TOKENS_JUDGE,
            temperature=0
        )
        chat_response = response.choices[0].message.content
        log.debug(f"[evaluate] Response from API: {chat_response}")
        return idx, chat_response


# -------- main --------------


async def main(args):
    global log

    os.makedirs(args.output, exist_ok=True)
    init_logger(args.output)

    mermseqbench_ds = load_dataset("ibm-research/MermaidSeqBench")
    df = mermseqbench_ds["train"].to_pandas()
    if args.limit:
        df = df.head(args.limit)
    log.info(f'Loaded data ({len(df)} rows):\n"{df}"...')

    with open(args.crit_file, 'r') as file:
        crit_config = yaml.safe_load(file)
    log.info(f"Loaded LLMaJ criteria ({len(crit_config['evaluation_criteria'])} in total)")

    sem = asyncio.Semaphore(args.concurrency)

    # LLM under test
    model = args.model
    endpoint = args.model_api_endpoint
    client = AsyncOpenAI(
        base_url=endpoint,
        api_key=os.environ[args.model_api_key],
    )
    log.info(f'Running LLM: {model} (concurrency={args.concurrency})')

    pbar = tqdm(total=len(df), desc=f"[{model}] generating")
    tasks = []
    for i, row in df.iterrows():
        user_prompt = row.get(LLM_PROMPT_COL)
        tasks.append(generate_one(sem, client, model, user_prompt, i))

    for coro in asyncio.as_completed(tasks):
        idx, result = await coro
        df.at[idx, LLM_OUTPUT_COL] = result
        pbar.update(1)
    pbar.close()

    # LLMaJ
    judge_model = args.judge
    judge_endpoint = args.judge_api_endpoint
    judge_client = AsyncOpenAI(
        base_url=judge_endpoint,
        api_key=os.environ[args.judge_api_key],
    )
    log.info(f'Running judge: {judge_model}')
    for criterion in tqdm(crit_config['evaluation_criteria'], desc=f"[{judge_model}] criteria"):
        log.info(f"Running criteria: {criterion['name']}")

        pbar = tqdm(total=len(df), desc=f"[{judge_model}] {criterion['name']}")
        tasks = []
        for i, row in df.iterrows():
            tasks.append(evaluate_one(
                sem, judge_client, judge_model,
                prompt_template=criterion["prompt_template"],
                agent_prompt=row.get(LLM_PROMPT_COL),
                agent_response=row.get(LLM_OUTPUT_COL),
                expected_agent_response=row.get(EXPECTED_OUTPUT_COL),
                idx=i))

        for coro in asyncio.as_completed(tasks):
            idx, judge_response = await coro
            df.at[idx, f"llm_judge_{criterion['name']}_response"] = judge_response
            df.at[idx, f"score_{criterion['name']}"] = extract_float_from_string(judge_response)
            pbar.update(1)
        pbar.close()

    # results
    score_columns = [col for col in df.columns if 'score_' in col]
    averages = df[score_columns].mean(skipna=True)

    log.info(f'Model: {model}\nJudge: {judge_model}\n\nMean scores over {len(df)} samples:\n{averages}\n')

    timestamp = datetime.now().strftime("%Y_%m_%d.%H_%M_%S")
    output_path = os.path.join(args.output, f'results__{timestamp}.csv')
    df.to_csv(output_path, index=False)
    log.info(f"Saved results to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate an LLM on the MermaidSeqBench dataset using LLMaJ with the RESTful OpenAI client.")
    parser.add_argument("--model", required=True, help="Name or identifier of the model to evaluate.")
    parser.add_argument("--model_api_endpoint", required=True, help="REST API endpoint for the model (e.g., OpenAI-compatible endpoint URL).")
    parser.add_argument("--judge", required=True, help="Name or identifier of the judging model.")
    parser.add_argument("--judge_api_endpoint", required=True, help="REST API endpoint for the judging model (LLMaJ).")
    parser.add_argument("--model_api_key", default="OPENAI_API_KEY", help="Name of the env variable holding the API key for the model (default: OPENAI_API_KEY).")
    parser.add_argument("--judge_api_key", default="OPENAI_API_KEY", help="Name of the env variable holding the API key for the judge (default: OPENAI_API_KEY).")
    parser.add_argument("--limit", type=int, default=None, help="Limit dataset to first N rows (default: no limit).")
    parser.add_argument("--concurrency", type=int, default=5, help="Max parallel API requests (default: 5).")
    parser.add_argument("--output", default="./", help="Output folder for the evaluation results and log file (default: current directory).")
    parser.add_argument("--crit_file", default="judge-criteria.yaml", help="Path to the YAML file defining judgment criteria (default: judge-criteria.yaml).")
    args = parser.parse_args()
    asyncio.run(main(args))
