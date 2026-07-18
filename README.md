# Practical AI Engineering for Finance

An 18-week, undergraduate-level course in Python, APIs, prompt engineering,
vector databases, retrieval-augmented generation (RAG), evaluation, testing,
and deployment.

**Schedule:** 1 hour per day, 4 days per week (Weeks 17–18 are optional,
6-day advanced extensions)  
**Total instructional time:** 76 hours  
**Audience:** College seniors in finance, business analytics, data science,
computer science, or related majors  
**Capstone:** AI-Powered Equity Research Assistant

## Course Website

After GitHub Pages is enabled, the course website will be available at:

`https://cj5815.github.io/practical-ai-engineering-finance/`

## Repository Structure

```text
docs/                    Course website and lessons
  setup/                 Mac, VS Code, Python, Git, and GitHub setup
  weeks/                 Weekly lesson plans
  projects/              Project specifications
  resources/             Reading and reference materials
src/
  ai_finance_course/     Reusable Python code built up week by week (Weeks 1-17)
  sec_thesis/            Standalone SEC-filing research CLI (Week 18+, own CLAUDE.md)
examples/                Runnable per-week demo scripts and notebooks
tests/                   Automated tests
notebooks/               Jupyter notebooks
data/sample/             Small, non-confidential sample datasets
.github/workflows/       Automated testing and site deployment
```

## sec_thesis CLI (Week 18+)

`sec_thesis` is a standalone CLI tool built starting Week 18 — see
[`src/sec_thesis/CLAUDE.md`](src/sec_thesis/CLAUDE.md) for its full project
spec. After `pip install -e .` (below), set `SEC_USER_AGENT` in `.env`
(see `.env.example`) and run:

```bash
sec-thesis resolve-cik AAPL
sec-thesis list-filings AAPL --forms 10-K,10-Q,8-K
sec-thesis fetch-filings AAPL
```

## Start Here

1. Read [`docs/setup/mac-vscode.md`](docs/setup/mac-vscode.md).
2. Complete Week 1.
3. Run the starter code and tests.
4. Commit your work after each class session.

## Local Setup

```bash
git clone https://github.com/YOUR-GITHUB-USERNAME/practical-ai-engineering-finance.git
cd practical-ai-engineering-finance

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -e ".[dev,docs]"

pytest
mkdocs serve
```

## Student Workflow

For each session:

1. Read the assigned lesson.
2. Complete the coding exercise.
3. Run `pytest`.
4. Update the weekly reflection.
5. Commit and push your work.

Example:

```bash
git add .
git commit -m "Complete Week 3 Day 2"
git push
```

## Instructor Options

- Use this repository directly as a public course.
- Mark it as a GitHub template repository.
- Create separate assignment repositories.
- Connect assignment repositories to GitHub Classroom.
- Use GitHub Issues for questions and office hours.
- Use pull requests for feedback and grading.

## License

Course text is licensed under CC BY 4.0. Code is licensed under the MIT License.
