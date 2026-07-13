# Mac and Visual Studio Code Setup

## 1. Understand the Main Tools

- **Terminal** lets you type commands to control your Mac.
- **Python** runs the programs you write.
- **VS Code** is the editor where you write and debug code.
- **Git** records changes to your project.
- **GitHub** stores the Git repository online.

## 2. Open Terminal

Press `Command + Space`, type `Terminal`, and press Return.

Check the current folder:

```bash
pwd
```

List files:

```bash
ls
```

Move into a folder:

```bash
cd Documents
```

Create a folder:

```bash
mkdir practical-ai-course
cd practical-ai-course
```

## 3. Install Homebrew

Homebrew is a package manager for macOS. Follow the instructions on the official
Homebrew website. After installation, verify it:

```bash
brew --version
```

## 4. Install Git and Python

```bash
brew install git python
git --version
python3 --version
```

Use Python 3.11 or later for this course.

## 5. Install VS Code

Install Visual Studio Code, open it, and add these extensions:

- Python
- Pylance
- Jupyter
- Ruff
- GitHub Pull Requests
- Markdown All in One

## 6. Open the Course Folder

From Terminal:

```bash
code .
```

If `code` is not recognized:

1. Open VS Code.
2. Press `Command + Shift + P`.
3. Search for `Shell Command: Install 'code' command in PATH`.
4. Restart Terminal and run `code .` again.

## 7. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

When active, the Terminal prompt should begin with `(.venv)`.

In VS Code:

1. Press `Command + Shift + P`.
2. Select `Python: Select Interpreter`.
3. Choose the Python interpreter inside `.venv`.

## 8. Install Course Packages

```bash
python -m pip install --upgrade pip
pip install -e ".[dev,docs]"
```

## 9. Run the Starter Program

```bash
python -m ai_finance_course.returns
```

## 10. Run Tests

```bash
pytest
```

## 11. VS Code Skills to Practice

- Explorer: open and create files
- Search: search across the repository
- Source Control: review Git changes
- Terminal: run commands without leaving VS Code
- Problems: find linting and syntax problems
- Debugger: pause a program and inspect variables

Useful shortcuts:

| Action | Shortcut |
|---|---|
| Command Palette | `Command + Shift + P` |
| Open Terminal | ``Control + ` `` |
| Search files | `Command + P` |
| Search repository | `Command + Shift + F` |
| Save | `Command + S` |
| Start debugging | `F5` |
