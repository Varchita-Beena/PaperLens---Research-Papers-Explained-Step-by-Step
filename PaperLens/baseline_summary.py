import json
import os
import subprocess
import sys

import requests


def extract_text_from_pdf(pdf_path):
    result = subprocess.run(
        ["pdftotext", pdf_path, "-"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise Exception("Could not extract text from PDF")

    return result.stdout


MODEL_NAME = "gpt-4.1-mini"


def call_openai(prompt, api_key):
    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }

    data = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": "You are a research paper assistant. Return only valid JSON.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.2,
    }

    response = requests.post(url, headers=headers, json=data, timeout=120)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()["choices"][0]["message"]["content"]


def make_baseline_prompt(paper_text):
    return """
Read this research paper and create a one-shot summary.

Explain:
1. What problem statement the paper tries to solve.
2. How this problem was approached previously.
3. How this paper approaches the problem.
4. What datasets are used.
5. What metrics are used.
6. What experiments were designed.
7. What results were found.
8. What conclusion the paper gives.
9. Limitations of one shot summary method

Return only JSON in this format:

{
  "problem_statement": "",
  "previous_approaches": "",
  "paper_approach": "",
  "datasets": [],
  "metrics": [],
  "experiments": [],
  "results": "",
  "conclusion": "",
  "limitations_of_one_shot_summary": []
}

Paper text:
""" + paper_text[:60000]


def save_json(path, data):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def run_baseline_summary(pdf_path, api_key):
    state = {}
    state["pdf_path"] = pdf_path

    paper_text = extract_text_from_pdf(pdf_path)
    state["paper_text_characters"] = len(paper_text)

    prompt = make_baseline_prompt(paper_text)
    state["prompt"] = prompt

    llm_output = call_openai(prompt, api_key)
    state["model"] = MODEL_NAME
    state["raw_llm_output"] = llm_output

    try:
        summary = json.loads(llm_output)
    except Exception:
        summary = {"raw_summary": llm_output}

    state["summary"] = summary

    save_json("PaperLens/outputs/baseline_state.json", state)
    save_json("PaperLens/outputs/baseline_summary.json", summary)

    return state


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 PaperLens/baseline_summary.py path/to/paper.pdf OPENAI_API_KEY")
        sys.exit(1)

    pdf_path = sys.argv[1]
    api_key = sys.argv[2]
    state = run_baseline_summary(pdf_path, api_key)

    print("Baseline summary complete")
    print("State saved at: PaperLens/outputs/baseline_state.json")
    print("Summary saved at: PaperLens/outputs/baseline_summary.json")
    print("Characters extracted:", state["paper_text_characters"])
