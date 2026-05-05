# PaperLens: Research Paper Simplifier Agent

PaperLens is a multi-step LLM agent that helps students understand research papers. The user gives a paper name or PDF link, and the agent downloads the paper, extracts text, studies different parts of the paper through multiple LLM calls, and produces structured JSON outputs and PPT content.

The project also includes a one-shot baseline summary, so the simple single-prompt approach can be compared with the multi-step agent.

## What The Agent Does

PaperLens can:

- Search for a paper using DuckDuckGo if the user gives a paper name
- Download a PDF if the user gives a paper link
- Extract text from the PDF using `pdftotext`
- Run a one-shot baseline summary
- Run a multi-step paper study chain
- Explain the problem statement, introduction, related work, methodology, datasets, experiments, and results
- Save every step output as JSON
- Combine all step outputs into a final JSON
- Generate PPT slide text and a `.pptx` presentation

## Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

The project also requires `pdftotext` for PDF text extraction.

On macOS, it can be installed with:

```bash
brew install poppler
```

## Inputs Expected

Each main script expects:

```text
paper name or paper link
OpenAI API key
```

Examples of valid paper inputs:

```text
Attention Is All You Need
https://arxiv.org/pdf/1706.03762
https://arxiv.org/abs/1706.03762
```

The API key should be passed from the CLI as the last argument.

## Files

### 1. `download_paper.py`

This is Step 1. It downloads the paper.

If the input is a link, it downloads the PDF directly. If the input is a paper name, it uses DuckDuckGo search to find a PDF/arXiv link and then downloads it.

Run:

```bash
python3 PaperLens/download_paper.py "Attention Is All You Need"
```

Expected output:

```text
PDF link
PDF path
PaperLens/outputs/step1_state.json
```

### 2. `baseline_summary.py`

This is the one-shot baseline.

It extracts the whole paper text and sends it to one LLM prompt. The goal is to show the limitation of doing everything in one call.

Run:

```bash
python3 PaperLens/baseline_summary.py "papers/your_paper.pdf" "sk-your-openai-key"
```

Expected output:

```text
PaperLens/outputs/baseline_state.json
PaperLens/outputs/baseline_summary.json
```

### 3. `study_paper.py`

This is the main multi-step version using section and keyword retrieval.

Chain:

```text
paper name/link
-> download paper
-> extract text
-> extract sections using headings/keywords
-> problem statement prompt
-> introduction prompt
-> related work prompt
-> methodology prompt
-> dataset prompt
-> experiment prompt
-> result prompt
-> final combined JSON
-> PPT slide JSON
-> PPT text and PPTX
```

Run:

```bash
python3 PaperLens/study_paper.py "Attention Is All You Need" "sk-your-openai-key"
```

Expected output folder:

```text
PaperLens/outputs/
```

Expected files:

```text
step1_state.json
sections.json
step3_problem.json
step4_introduction.json
step5_related_work.json
step6_methodology.json
step7_datasets.json
step8_experiments.json
step9_results.json
step10_final_combined.json
step11_ppt_slides.json
presentation_text.txt
presentation.pptx
current_state.json
full_state.json
```

### 4. `study_paper_semantic.py`

This version uses semantic search with embeddings.

Instead of relying only on section headings, it splits the paper into chunks, creates embeddings using OpenAI embeddings, and retrieves the most relevant chunks using cosine similarity.

Chain:

```text
paper name/link
-> download paper
-> extract text
-> split into chunks
-> create embeddings
-> retrieve top chunks for each step
-> run the same multi-step prompts
-> final JSON
-> PPT output
```

Run:

```bash
python3 PaperLens/study_paper_semantic.py "Attention Is All You Need" "sk-your-openai-key"
```

Expected output folder:

```text
PaperLens/outputs_semantic/
```

Expected files:

```text
chunks_without_embeddings.json
chunks_with_embeddings.json
chunks_problem.json
chunks_introduction.json
chunks_related_work.json
chunks_methodology.json
chunks_datasets.json
chunks_experiments.json
chunks_results.json
semantic_step3_problem.json
semantic_step4_introduction.json
semantic_step5_related_work.json
semantic_step6_methodology.json
semantic_step7_datasets.json
semantic_step8_experiments.json
semantic_step9_results.json
semantic_step10_final_combined.json
semantic_step11_ppt_slides.json
presentation_text.txt
presentation.pptx
current_state.json
full_state.json
```

### 5. `study_paper_routing.py`

This version uses LLM-based routing.

It splits the paper into chunks and creates short previews of each chunk. The LLM chooses which chunk IDs are useful for each step. Then the code retrieves the full chunks and passes them to the step prompt.

Chain:

```text
paper name/link
-> download paper
-> extract text
-> split into chunks
-> send chunk previews to LLM
-> LLM selects chunk IDs
-> code retrieves full selected chunks
-> run the same multi-step prompts
-> final JSON
-> PPT output
```

Run:

```bash
python3 PaperLens/study_paper_routing.py "Attention Is All You Need" "sk-your-openai-key"
```

Expected output folder:

```text
PaperLens/outputs_routing/
```

Expected files:

```text
chunks.json
route_problem.json
route_introduction.json
route_related_work.json
route_methodology.json
route_datasets.json
route_experiments.json
route_results.json
chunks_problem.json
chunks_introduction.json
chunks_related_work.json
chunks_methodology.json
chunks_datasets.json
chunks_experiments.json
chunks_results.json
routing_step3_problem.json
routing_step4_introduction.json
routing_step5_related_work.json
routing_step6_methodology.json
routing_step7_datasets.json
routing_step8_experiments.json
routing_step9_results.json
routing_step10_final_combined.json
routing_step11_ppt_slides.json
presentation_text.txt
presentation.pptx
current_state.json
full_state.json
```

### 6. `skills/ppt_writer/skill.md`

This file contains reusable PPT-writing instructions. The agent loads this skill after the final JSON is created. The skill tells the LLM how to create student-friendly slides.

It asks for:

```text
slide title
bullet points
speaker notes
visual suggestion
```

The slide JSON is then converted into:

```text
presentation_text.txt
presentation.pptx
```

## Model Used

The current LLM model is:

```text
gpt-4.1-mini
```

The semantic version also uses:

```text
text-embedding-3-small
```

## Notes

The PPTX generation uses `python-pptx`. If PPTX is not created, install it using:

```bash
python3 -m pip install python-pptx
```

If the script uses a different Python environment, install it with the Python path printed by the script.

## Limitations

PaperLens currently reads only text from PDFs. It does not understand figures, architecture diagrams, plots, scanned pages, or equations stored as images. Section extraction can also fail when papers use unusual headings. The generated PPT is a useful first draft, but it is not a polished presentation design.
