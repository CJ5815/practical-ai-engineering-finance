# Capstone: AI-Powered Equity Research Assistant

## Problem

Investment analysts work with filings, earnings materials, news, notes, and
financial data. The capstone should help a user locate relevant evidence and
form a more organized initial view of a company.

## Minimum Features

1. Load at least three public company documents.
2. Split documents into retrievable chunks.
3. Store chunks and metadata in a vector database.
4. Retrieve evidence for a natural-language question.
5. Generate an answer based only on retrieved evidence.
6. Display source names or citations.
7. Provide at least 15 evaluation questions.
8. Include automated tests.
9. Expose the system through a CLI or FastAPI endpoint.
10. Provide setup and usage instructions.

## Recommended Repository Layout

```text
src/
  ingestion/
  retrieval/
  generation/
  evaluation/
  api/
tests/
data/sample/
docs/
```

## Required Documentation

The final README must explain:

- the problem;
- the target user;
- the architecture;
- setup instructions;
- example questions;
- evaluation results;
- known limitations;
- future improvements.

## Interview Demonstration

Prepare a five-minute demonstration:

1. State the problem.
2. Explain the architecture.
3. Ask one successful question.
4. Show one failure case.
5. Explain what you learned and what you would improve.
