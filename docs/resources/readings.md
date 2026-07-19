# Papers and Reading

The student is not expected to understand every equation. For each paper,
focus on the problem, core idea, evidence, limitations, and connection to the
course project.

## Python and Development

- *Python Crash Course* — Eric Matthes, selected chapters
- *Automate the Boring Stuff with Python* — Al Sweigart, selected chapters
- Official Python tutorial
- Official VS Code Python documentation
- Pro Git, Chapters 1–3

## APIs and Software

- HTTP and REST introductory documentation
- Twelve-Factor App, especially configuration and logs
- FastAPI tutorial
- pytest documentation

## LLMs and Prompting

- Vaswani et al., [**Attention Is All You Need**](papers/attention-is-all-you-need.pdf)
- Brown et al., [**Language Models are Few-Shot Learners**](papers/few-shot-learners.pdf)
- Wei et al., [**Chain-of-Thought Prompting Elicits Reasoning in Large Language Models**](papers/chain-of-thought-prompting.pdf)
- Yao et al., [**ReAct: Synergizing Reasoning and Acting in Language Models**](papers/react-reasoning-and-acting.pdf)

## Embeddings and Retrieval

- Reimers and Gurevych, [**Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks**](papers/sentence-bert.pdf) — published at EMNLP-IJCNLP 2019.
- Karpukhin et al., [**Dense Passage Retrieval for Open-Domain Question Answering**](papers/dense-passage-retrieval.pdf) — published at EMNLP 2020.
- Lewis et al., [**Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks**](papers/retrieval-augmented-generation.pdf) — the original RAG paper, published at NeurIPS 2020.
- Khattab and Zaharia, [**ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT**](papers/colbert.pdf) — the original ColBERT paper, published at SIGIR 2020.

A useful reading order is **Sentence-BERT → DPR → ColBERT → RAG**: Sentence-BERT introduces efficient embedding comparison; DPR applies dense dual encoders to passage retrieval; ColBERT adds token-level late interaction; and RAG combines retrieval with language generation.

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

## Reading Note Template

For every paper, answer:

1. What problem does the paper address?
2. What is the main idea?
3. What evidence supports it?
4. What assumptions does it make?
5. What are its limitations?
6. How could the idea improve the capstone?
