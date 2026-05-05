import json
import os
import re
import sys
import requests


def is_link(user_input):
    return user_input.startswith("http://") or user_input.startswith("https://")


def make_ddg_call(query, max_results=5):
    from ddgs import DDGS

    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
    return results


def save_json(path, data):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_pdf_link_from_results(results):
    for result in results:
        link = result.get("href", "")

        if link.endswith(".pdf") or "arxiv.org/pdf" in link:
            return link

        if "arxiv.org/abs/" in link:
            return link.replace("/abs/", "/pdf/")

    return None


def clean_filename(name):
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")
    return name[:80]


def download_pdf(pdf_link, save_folder="papers", filename="paper"):
    os.makedirs(save_folder, exist_ok=True)

    save_path = os.path.join(save_folder, filename + ".pdf")

    response = requests.get(pdf_link, timeout=30)

    if response.status_code != 200:
        raise Exception("Could not download PDF")

    if not response.content.startswith(b"%PDF"):
        raise Exception("Downloaded file does not look like a PDF")

    with open(save_path, "wb") as f:
        f.write(response.content)

    return save_path


def step1_download_paper(user_input):
    state = {}
    state["user_input"] = user_input
    state["search_results"] = []
    state["pdf_link"] = None
    state["pdf_path"] = None

    if is_link(user_input):
        pdf_link = user_input
        if "arxiv.org/abs/" in pdf_link:
            pdf_link = pdf_link.replace("/abs/", "/pdf/")
    else:
        query = user_input + " research paper pdf"
        results = make_ddg_call(query)
        state["search_results"] = results

        pdf_link = get_pdf_link_from_results(results)

        if pdf_link is None:
            raise Exception("No valid PDF link found from DuckDuckGo results")

    filename = clean_filename(user_input)
    pdf_path = download_pdf(pdf_link, filename=filename)

    state["pdf_link"] = pdf_link
    state["pdf_path"] = pdf_path

    save_json("PaperLens/outputs/step1_state.json", state)

    return state


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 PaperLens/download_paper.py \"paper name or paper link\"")
        sys.exit(1)

    paper = " ".join(sys.argv[1:])

    state = step1_download_paper(paper)

    print("Step 1 complete")
    print("PDF link:", state["pdf_link"])
    print("Saved at:", state["pdf_path"])
    print("State saved at: PaperLens/outputs/step1_state.json")
