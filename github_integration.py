from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def report_issue(title, description):
    OUTPUT_DIR.mkdir(exist_ok=True)
    file_path = OUTPUT_DIR / "github_issue.txt"
    issue = f"Title: {title}\n\nDescription:\n{description}"
    file_path.write_text(issue, encoding="utf-8")
    return str(file_path)
