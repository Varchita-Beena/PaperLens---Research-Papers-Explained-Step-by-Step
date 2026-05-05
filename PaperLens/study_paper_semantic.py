import json
import math
import os
import sys

import requests

from baseline_summary import call_openai
from baseline_summary import extract_text_from_pdf
from download_paper import step1_download_paper
from study_paper import clean_json
from study_paper import make_ppt_prompt
from study_paper import make_pptx
from study_paper import save_json
from study_paper import save_ppt_text
from study_paper import step10_final_prompt
from study_paper import step3_problem_prompt
from study_paper import step4_intro_prompt
from study_paper import step5_related_work_prompt
from study_paper import step6_methodology_prompt
from study_paper import step7_datasets_prompt
from study_paper import step8_experiments_prompt
from study_paper import step9_results_prompt


EMBEDDING_MODEL = "text-embedding-3-small"


def make_chunks(paper_text, words_per_chunk=350):
    words = paper_text.split()
    chunks = []

    for i in range(0, len(words), words_per_chunk):
        chunk_text = " ".join(words[i:i + words_per_chunk])
        chunks.append({
            "chunk_id": len(chunks),
            "text": chunk_text,
        })

    return chunks


def get_embedding(text, api_key):
    url = "https://api.openai.com/v1/embeddings"

    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }

    data = {
        "model": EMBEDDING_MODEL,
        "input": text,
    }

    response = requests.post(url, headers=headers, json=data, timeout=60)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()["data"][0]["embedding"]


def cosine_similarity(a, b):
    dot = 0
    norm_a = 0
    norm_b = 0

    for x, y in zip(a, b):
        dot = dot + x * y
        norm_a = norm_a + x * x
        norm_b = norm_b + y * y

    if norm_a == 0 or norm_b == 0:
        return 0

    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def add_embeddings_to_chunks(chunks, api_key):
    for chunk in chunks:
        print("Embedding chunk", chunk["chunk_id"] + 1, "of", len(chunks))
        chunk["embedding"] = get_embedding(chunk["text"], api_key)

    return chunks


def retrieve_chunks(chunks, query, api_key, top_k=4):
    query_embedding = get_embedding(query, api_key)
    scored_chunks = []

    for chunk in chunks:
        score = cosine_similarity(query_embedding, chunk["embedding"])
        scored_chunks.append((score, chunk))

    scored_chunks.sort(reverse=True, key=lambda item: item[0])

    selected = []
    for score, chunk in scored_chunks[:top_k]:
        selected.append({
            "chunk_id": chunk["chunk_id"],
            "score": score,
            "text": chunk["text"],
        })

    return selected


def chunks_to_text(selected_chunks):
    text_parts = []

    for chunk in selected_chunks:
        text_parts.append(
            "[Chunk " + str(chunk["chunk_id"]) + ", score " + str(round(chunk["score"], 3)) + "]\n" + chunk["text"]
        )

    return "\n\n".join(text_parts)


def retrieve_and_save(state, chunks, name, query, api_key):
    selected = retrieve_chunks(chunks, query, api_key)

    state["semantic_chunks_" + name] = selected
    save_json("PaperLens/outputs_semantic/chunks_" + name + ".json", selected)

    return chunks_to_text(selected)


def ask_semantic_step(step_name, prompt, api_key, state):
    print("Running", step_name)

    llm_output = call_openai(prompt, api_key)
    parsed_output = clean_json(llm_output)

    state[step_name] = parsed_output
    state["raw_" + step_name] = llm_output

    save_json("PaperLens/outputs_semantic/" + step_name + ".json", parsed_output)
    save_json("PaperLens/outputs_semantic/current_state.json", state)

    return parsed_output


def run_semantic_study(paper_input, api_key):
    state = {}
    state["paper_input"] = paper_input
    state["retrieval_method"] = "semantic_search_embeddings"
    state["embedding_model"] = EMBEDDING_MODEL

    print("Running step1_download_paper")
    step1 = step1_download_paper(paper_input)
    state["step1_download"] = step1
    state["pdf_path"] = step1["pdf_path"]

    print("Running step2_extract_text_and_make_chunks")
    paper_text = extract_text_from_pdf(state["pdf_path"])
    state["paper_text_characters"] = len(paper_text)

    chunks = make_chunks(paper_text)
    state["number_of_chunks"] = len(chunks)
    save_json("PaperLens/outputs_semantic/chunks_without_embeddings.json", chunks)

    chunks = add_embeddings_to_chunks(chunks, api_key)
    save_json("PaperLens/outputs_semantic/chunks_with_embeddings.json", chunks)

    state["sections"] = {}
    state["sections"]["abstract"] = retrieve_and_save(
        state,
        chunks,
        "problem",
        "abstract introduction problem statement motivation contribution",
        api_key,
    )
    state["sections"]["introduction"] = state["sections"]["abstract"]

    ask_semantic_step("semantic_step3_problem", step3_problem_prompt(state), api_key, state)
    state["step3_problem"] = state["semantic_step3_problem"]

    state["sections"]["introduction"] = retrieve_and_save(
        state,
        chunks,
        "introduction",
        "introduction motivation background contribution problem gap",
        api_key,
    )

    ask_semantic_step("semantic_step4_introduction", step4_intro_prompt(state), api_key, state)
    state["step4_introduction"] = state["semantic_step4_introduction"]

    state["sections"]["related_work"] = retrieve_and_save(
        state,
        chunks,
        "related_work",
        "related work previous approaches prior methods background limitations",
        api_key,
    )

    ask_semantic_step("semantic_step5_related_work", step5_related_work_prompt(state), api_key, state)
    state["step5_related_work"] = state["semantic_step5_related_work"]

    state["sections"]["methodology"] = retrieve_and_save(
        state,
        chunks,
        "methodology",
        "method methodology model architecture algorithm equations proposed approach",
        api_key,
    )

    ask_semantic_step("semantic_step6_methodology", step6_methodology_prompt(state), api_key, state)
    state["step6_methodology"] = state["semantic_step6_methodology"]

    state["dataset_text"] = retrieve_and_save(
        state,
        chunks,
        "datasets",
        "datasets training data test set benchmark corpus evaluation data WMT",
        api_key,
    )

    ask_semantic_step("semantic_step7_datasets", step7_datasets_prompt(state), api_key, state)
    state["step7_datasets"] = state["semantic_step7_datasets"]

    state["sections"]["experiments"] = retrieve_and_save(
        state,
        chunks,
        "experiments",
        "experiments experimental setup baselines metrics ablation training details evaluation",
        api_key,
    )

    ask_semantic_step("semantic_step8_experiments", step8_experiments_prompt(state), api_key, state)
    state["step8_experiments"] = state["semantic_step8_experiments"]

    state["sections"]["results"] = retrieve_and_save(
        state,
        chunks,
        "results",
        "results scores performance comparison tables metrics BLEU accuracy conclusion",
        api_key,
    )
    state["sections"]["conclusion"] = retrieve_and_save(
        state,
        chunks,
        "conclusion",
        "conclusion discussion findings future work limitations",
        api_key,
    )

    ask_semantic_step("semantic_step9_results", step9_results_prompt(state), api_key, state)
    state["step9_results"] = state["semantic_step9_results"]

    ask_semantic_step("semantic_step10_final_combined", step10_final_prompt(state), api_key, state)
    state["step10_final_combined"] = state["semantic_step10_final_combined"]

    ppt_output = ask_semantic_step("semantic_step11_ppt_slides", make_ppt_prompt(state), api_key, state)
    slides = ppt_output.get("slides", [])
    save_ppt_text(slides, "PaperLens/outputs_semantic/presentation_text.txt")
    make_pptx(slides, "PaperLens/outputs_semantic/presentation.pptx")

    save_json("PaperLens/outputs_semantic/full_state.json", state)

    return state


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 PaperLens/study_paper_semantic.py paper name or paper link OPENAI_API_KEY")
        sys.exit(1)

    paper_input = " ".join(sys.argv[1:-1])
    api_key = sys.argv[-1]

    os.makedirs("PaperLens/outputs_semantic", exist_ok=True)
    run_semantic_study(paper_input, api_key)

    print("Semantic paper study complete")
    print("All outputs saved in: PaperLens/outputs_semantic")
    print("Final JSON: PaperLens/outputs_semantic/semantic_step10_final_combined.json")
    print("PPT text: PaperLens/outputs_semantic/presentation_text.txt")
    print("PPTX: PaperLens/outputs_semantic/presentation.pptx")
    print("Full state: PaperLens/outputs_semantic/full_state.json")
