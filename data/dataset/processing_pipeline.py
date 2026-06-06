import os
import json
import requests
from pathlib import Path
from tqdm import tqdm

API_URL = "http://localhost:8080/refactor-online"

#MODELS = ["codeqwen:7b", "deepseek-coder:6.7b",  "codegemma:7b"]
#MODELS = ["codeqwen:7b"]
MODELS = ["gpt-4o-mini"]
STRATEGIES = ["ENSEMBLE", "EXAMPLE","DEFAULT","SMELL"]
#STRATEGIES = ["TAGGING"]
#INPUT_FILES = ["isp_violations.json"]
INPUT_FILES = ["srp_violations.json", "ocp_violations.json", "lsp_violations.json", "isp_violations.json"]
#INPUT_FILES = ["mixed.json"]

INPUT_DIR = Path(".")
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

def call_refactor_api(model, strategy, source_code, language):
    payload = {
        "model": model,
        "strategy": strategy,
        "temperature": 0,
        "source": source_code,
        "try_count": 1,
        "language": language
    }
    response = requests.post(API_URL, json=payload)
    response.raise_for_status()
    return response.text

def parse_response(response_str):
    try:
        response_data = json.loads(response_str)
        return {
            "type": response_data.get("violation_type", ""),
            "refactored_code": response_data.get("refactored_code", response_str),
            "explanation": response_data.get("explanation", "")
        }
    except json.JSONDecodeError:
        print("Failed to decode JSON from response")
        return {
            "type": "",
            "refactored_code": "",

            "explanation": response_str
        }

def process_file(filepath):
    with open(filepath, "r") as f:
        data = json.load(f)

    base_name = filepath.stem

    for model in tqdm(MODELS, desc="Models"):
        for strategy in tqdm(STRATEGIES, desc=f"Strategies for {model}", leave=False):
            updated_data = {"code_examples": []}
            examples = data.get("code_examples", [])
            for example in tqdm(examples, desc=f"Examples ({model}/{strategy})", leave=False):
                response = call_refactor_api(model, strategy, example["input"], example["language"])
                parsed = parse_response(response)
                example["output"] = parsed["refactored_code"]
                example["violation"] = parsed["type"]
                example["explanation"] = parsed["explanation"]
                updated_data["code_examples"].append(example)

            output_filename = f"{base_name}_{model.replace(':', '-')}_{strategy}.json"
            with open(OUTPUT_DIR / output_filename, "w") as out_file:
                json.dump(updated_data, out_file, indent=4)

# Process all JSON files in the current directory
if __name__ == '__main__':
    input_paths = [Path(f) for f in INPUT_FILES]
    for file in input_paths:
        process_file(file)
