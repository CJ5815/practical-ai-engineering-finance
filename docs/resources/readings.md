# Papers and Reading

The student is not expected to understand every equation. For each paper,
focus on the problem, core idea, evidence, limitations, and connection to the
course project.

## Python and Development

- *Python Crash Course* — Eric Matthes, selected chapters. [Official book page](https://nostarch.com/python-crash-course-3rd-edition) (No Starch Press) — this is a paid, copyrighted book; no PDF is provided here.
- *Automate the Boring Stuff with Python* — Al Sweigart, selected chapters. Read free at the [official site](https://automatetheboringstuff.com/), published there directly by the author under a Creative Commons license.
- [Official Python tutorial](https://docs.python.org/3/tutorial/index.html)
- [Official VS Code Python documentation](https://code.visualstudio.com/docs/languages/python)
- [**Pro Git**](papers/pro-git.pdf), Chapters 1–3 — the official, freely licensed (CC BY-NC-SA) PDF of the full book; read "Getting Started," "Git Basics," and "Git Branching."

## APIs and Software

- [HTTP and REST introductory documentation](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview) (MDN)
- Twelve-Factor App, especially [configuration](https://12factor.net/config) and [logs](https://12factor.net/logs)
- [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/)
- [pytest documentation](https://docs.pytest.org/en/stable/)

## LLMs and Prompting

- Vaswani et al., [**Attention Is All You Need**](papers/attention-is-all-you-need.pdf)
- Brown et al., [**Language Models are Few-Shot Learners**](papers/few-shot-learners.pdf)
- Wei et al., [**Chain-of-Thought Prompting Elicits Reasoning in Large Language Models**](papers/chain-of-thought-prompting.pdf)
- Yao et al., [**ReAct: Synergizing Reasoning and Acting in Language Models**](papers/react-reasoning-and-acting.pdf)
- Ouyang et al., [**Training Language Models to Follow Instructions with Human Feedback**](papers/instructgpt.pdf) — the InstructGPT/RLHF paper explaining why instruction-following and prompting work the way they do.
- Wang et al., [**Self-Consistency Improves Chain of Thought Reasoning in Language Models**](papers/self-consistency.pdf) — a direct follow-up to the Chain-of-Thought paper above.
- Bai et al., [**Constitutional AI: Harmlessness from AI Feedback**](papers/constitutional-ai.pdf) — Anthropic's alignment approach, relevant since this course runs on Claude.
- Schick et al., [**Toolformer: Language Models Can Teach Themselves to Use Tools**](papers/toolformer.pdf) — complements ReAct above; directly relevant to the API-calling weeks (4–5).

## Embeddings and Retrieval

- Reimers and Gurevych, [**Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks**](papers/sentence-bert.pdf) — published at EMNLP-IJCNLP 2019.
- Karpukhin et al., [**Dense Passage Retrieval for Open-Domain Question Answering**](papers/dense-passage-retrieval.pdf) — published at EMNLP 2020.
- Lewis et al., [**Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks**](papers/retrieval-augmented-generation.pdf) — the original RAG paper, published at NeurIPS 2020.
- Khattab and Zaharia, [**ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT**](papers/colbert.pdf) — the original ColBERT paper, published at SIGIR 2020.

A useful reading order is **Sentence-BERT → DPR → ColBERT → RAG**: Sentence-BERT introduces efficient embedding comparison; DPR applies dense dual encoders to passage retrieval; ColBERT adds token-level late interaction; and RAG combines retrieval with language generation.

### Advanced RAG Techniques

- Liu et al., [**Lost in the Middle: How Language Models Use Long Contexts**](papers/lost-in-the-middle.pdf) — retrieved-evidence position matters; directly relevant to building the capstone's RAG pipeline.
- Gao et al., [**Precise Zero-Shot Dense Retrieval without Relevance Labels**](papers/hyde-dense-retrieval.pdf) — the HyDE query-rewriting technique, matching Week 11's "query rewriting" topic.
- Asai et al., [**Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection**](papers/self-rag.pdf) — an advanced retrieval-and-critique technique, another Week 11 candidate.

## Evaluation

- Es et al., [**RAGAS: Automated Evaluation of Retrieval Augmented Generation**](papers/ragas.pdf) — introduces reference-free metrics for evaluating both the retrieval and generation components of a RAG system.
- Liang et al., [**Holistic Evaluation of Language Models**](papers/helm.pdf) — introduces HELM, a framework for evaluating language models across multiple scenarios and dimensions, including accuracy, calibration, robustness, fairness, bias, toxicity, and efficiency.

### Framework Documentation: Ragas

[Ragas](https://docs.ragas.io/) is especially relevant here because it directly implements methods for evaluating RAG pipelines and other LLM applications. Its documentation covers evaluation datasets, metrics, test-set generation, experiments, and evaluation workflows.

Start with these official pages:

- [Ragas documentation home](https://docs.ragas.io/)
- [Evaluate a simple LLM application](https://docs.ragas.io/en/stable/getstarted/evals/)
- [Available evaluation metrics](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/)
- [Ragas GitHub repository](https://github.com/explodinggradients/ragas)

The most important RAG metrics to study:

- **Faithfulness** — whether the answer is supported by the retrieved context.
- **Answer relevancy** — whether the response actually addresses the question.
- **Context precision** — whether the most useful retrieved passages appear near the top.
- **Context recall** — whether the retrieved context contains the information needed to answer the question.

A good reading sequence is **HELM → RAGAS paper → Ragas quickstart → Ragas metrics documentation**: HELM provides the broad theory of model evaluation, while RAGAS applies evaluation specifically to retrieval-augmented systems.

## LLMs and Finance

- Wu et al., [**BloombergGPT: A Large Language Model for Finance**](papers/bloomberggpt.pdf) — the flagship domain-specific finance LLM, trained on a mix of general and financial text.
- Araci, [**FinBERT: Financial Sentiment Analysis with Pre-trained Language Models**](papers/finbert.pdf) — a smaller, classic finance-NLP paper on sentiment analysis.
- Yang et al., [**FinGPT: Open-Source Financial Large Language Models**](papers/fingpt.pdf) — an open-source alternative to BloombergGPT.
- Chen et al., [**FinQA: A Dataset of Numerical Reasoning over Financial Data**](papers/finqa.pdf) — numerical reasoning over financial tables and text, directly relevant to the capstone (10-Ks mix both).
- Yang et al., [**Large Language Models in Finance: A Survey**](papers/llms-in-finance-survey.pdf) — a broad survey tying the finance-LLM space together; a good starting point for this section.

## Reading Note Template

For every paper, answer:

1. What problem does the paper address?
2. What is the main idea?
3. What evidence supports it?
4. What assumptions does it make?
5. What are its limitations?
6. How could the idea improve the capstone?
