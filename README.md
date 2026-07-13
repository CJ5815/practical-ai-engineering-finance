# Practical AI Engineering for Finance

A 16-week, undergraduate-level course in Python, APIs, prompt engineering,
vector databases, retrieval-augmented generation (RAG), evaluation, testing,
and deployment.

**Schedule:** 1 hour per day, 4 days per week  
**Total instructional time:** 64 hours  
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
src/                     Reusable Python code
tests/                   Automated tests
notebooks/               Jupyter notebooks
data/sample/             Small, non-confidential sample datasets
.github/workflows/       Automated testing and site deployment
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
