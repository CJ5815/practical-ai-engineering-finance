# Git and GitHub

## Core Idea

Git saves versions of a project. GitHub stores those versions online and makes
collaboration, review, and publishing easier.

## Initial Setup

```bash
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
```

## Daily Workflow

```bash
git status
git add .
git commit -m "Describe the completed work"
git push
```

## Create the GitHub Repository

1. Sign into GitHub.
2. Create a new repository named `practical-ai-engineering-finance`.
3. Do not add another README if you are uploading this prepared repository.
4. In Terminal, run the commands GitHub displays under **push an existing repository**.

Typical commands:

```bash
git init
git add .
git commit -m "Create course repository"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/practical-ai-engineering-finance.git
git push -u origin main
```

## Good Commit Messages

- `Complete Week 2 return calculator`
- `Add SEC API error handling`
- `Test document chunking`
- `Document capstone setup`

Avoid messages such as `stuff`, `changes`, or `update`.
