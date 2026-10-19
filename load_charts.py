from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def generate_charts():
    OUTPUT_DIR.mkdir(exist_ok=True)
    file_path = OUTPUT_DIR / "load_charts.txt"
    file_path.write_text("Load chart summary\n- Safe limit: 16t\n- Recommended margin: 12%", encoding="utf-8")
    return str(file_path)
