import json
import os
import sys

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


def make_chunks(paper_text, words_per_chunk=350):
    words = paper_text.split()
    chunks = []

    for i in range(0, len(words), words_per_chunk):
        chunk_text = " ".join(words[i:i + words_per_chunk])
        chunks.append({
            "chunk_id": len(chunks),
            "text": chunk_text,
            "preview": chunk_text[:700],
        })

    return chunks


def ask_routing_step(step_name, prompt, api_key, state):
    print("Running", step_name)

    llm_output = call_openai(prompt, api_key)
    parsed_output = clean_json(llm_output)

    state[step_name] = parsed_output
    state["raw_" + step_name] = llm_output

    save_json("PaperLens/outputs_routing/" + step_name + ".json", parsed_output)
    save_json("PaperLens/outputs_routing/current_state.json", state)

    return parsed_output


def make_chunk_list_for_llm(chunks):
    lines = []

    for chunk in chunks:
        lines.append(
            "Chunk "
            + str(chunk["chunk_id"])
            + ": "
            + chunk["preview"].replace("\n", " ")
        )

    return "\n\n".join(lines)


def route_chunks(chunks, task, api_key, state, name):
    prompt = """
You are routing paper chunks to the correct research paper analysis step.

Task:
""" + task + """

Choose the most useful chunks for this task.
Return only JSON:
{
  "selected_chunk_ids": [],
  "reason": ""
}

Paper chunks:
""" + make_chunk_list_for_llm(chunks)

    output = ask_routing_step("route_" + name, prompt, api_key, state)
    selected_ids = output.get("selected_chunk_ids", [])

    selected_chunks = []
    for chunk in chunks:
        if chunk["chunk_id"] in selected_ids:
            selected_chunks.append(chunk)

    if len(selected_chunks) == 0:
        selected_chunks = chunks[:4]

    save_json("PaperLens/outputs_routing/chunks_" + name + ".json", selected_chunks)

    return chunks_to_text(selected_chunks)


def chunks_to_text(chunks):
    parts = []

    for chunk in chunks:
        parts.append("[Chunk " + str(chunk["chunk_id"]) + "]\n" + chunk["text"])

    return "\n\n".join(parts)


def run_routing_study(paper_input, api_key):
    state = {}
    state["paper_input"] = paper_input
    state["retrieval_method"] = "llm_based_routing"

    print("Running step1_download_paper")
    step1 = step1_download_paper(paper_input)
    state["step1_download"] = step1
    state["pdf_path"] = step1["pdf_path"]

    print("Running step2_extract_text_and_make_chunks")
    paper_text = extract_text_from_pdf(state["pdf_path"])
    state["paper_text_characters"] = len(paper_text)

    chunks = make_chunks(paper_text)
    state["number_of_chunks"] = len(chunks)
    save_json("PaperLens/outputs_routing/chunks.json", chunks)

    state["sections"] = {}

    state["sections"]["abstract"] = route_chunks(
        chunks,
        "Find chunks useful for explaining the paper problem statement, abstract, motivation, and main contribution.",
        api_key,
        state,
        "problem",
    )
    state["sections"]["introduction"] = state["sections"]["abstract"]

    ask_routing_step("routing_step3_problem", step3_problem_prompt(state), api_key, state)
    state["step3_problem"] = state["routing_step3_problem"]

    state["sections"]["introduction"] = route_chunks(
        chunks,
        "Find chunks useful for explaining the introduction, background, motivation, gap, and claimed contributions.",
        api_key,
        state,
        "introduction",
    )

    ask_routing_step("routing_step4_introduction", step4_intro_prompt(state), api_key, state)
    state["step4_introduction"] = state["routing_step4_introduction"]

    state["sections"]["related_work"] = route_chunks(
        chunks,
        "Find chunks useful for explaining related work, previous approaches, background methods, and limitations of older work.",
        api_key,
        state,
        "related_work",
    )

    ask_routing_step("routing_step5_related_work", step5_related_work_prompt(state), api_key, state)
    state["step5_related_work"] = state["routing_step5_related_work"]

    state["sections"]["methodology"] = route_chunks(
        chunks,
        "Find chunks useful for explaining methodology, proposed method, model architecture, equations, and algorithm.",
        api_key,
        state,
        "methodology",
    )

    ask_routing_step("routing_step6_methodology", step6_methodology_prompt(state), api_key, state)
    state["step6_methodology"] = state["routing_step6_methodology"]

    state["dataset_text"] = route_chunks(
        chunks,
        "Find chunks useful for explaining datasets, training data, test data, benchmarks, corpus, and evaluation data.",
        api_key,
        state,
        "datasets",
    )

    ask_routing_step("routing_step7_datasets", step7_datasets_prompt(state), api_key, state)
    state["step7_datasets"] = state["routing_step7_datasets"]

    state["sections"]["experiments"] = route_chunks(
        chunks,
        "Find chunks useful for explaining experiments, experimental setup, baselines, metrics, ablation studies, and evaluation settings.",
        api_key,
        state,
        "experiments",
    )

    ask_routing_step("routing_step8_experiments", step8_experiments_prompt(state), api_key, state)
    state["step8_experiments"] = state["routing_step8_experiments"]

    state["sections"]["results"] = route_chunks(
        chunks,
        "Find chunks useful for explaining results, scores, tables, comparisons, performance, metrics, and findings.",
        api_key,
        state,
        "results",
    )
    state["sections"]["conclusion"] = route_chunks(
        chunks,
        "Find chunks useful for explaining conclusion, discussion, findings, limitations, and future work.",
        api_key,
        state,
        "conclusion",
    )

    ask_routing_step("routing_step9_results", step9_results_prompt(state), api_key, state)
    state["step9_results"] = state["routing_step9_results"]

    ask_routing_step("routing_step10_final_combined", step10_final_prompt(state), api_key, state)
    state["step10_final_combined"] = state["routing_step10_final_combined"]

    ppt_output = ask_routing_step("routing_step11_ppt_slides", make_ppt_prompt(state), api_key, state)
    slides = ppt_output.get("slides", [])
    save_ppt_text(slides, "PaperLens/outputs_routing/presentation_text.txt")
    make_pptx(slides, "PaperLens/outputs_routing/presentation.pptx")

    save_json("PaperLens/outputs_routing/full_state.json", state)

    return state


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 PaperLens/study_paper_routing.py paper name or paper link OPENAI_API_KEY")
        sys.exit(1)

    paper_input = " ".join(sys.argv[1:-1])
    api_key = sys.argv[-1]

    os.makedirs("PaperLens/outputs_routing", exist_ok=True)
    run_routing_study(paper_input, api_key)

    print("LLM-routing paper study complete")
    print("All outputs saved in: PaperLens/outputs_routing")
    print("Final JSON: PaperLens/outputs_routing/routing_step10_final_combined.json")
    print("PPT text: PaperLens/outputs_routing/presentation_text.txt")
    print("PPTX: PaperLens/outputs_routing/presentation.pptx")
    print("Full state: PaperLens/outputs_routing/full_state.json")
