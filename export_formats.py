import json
import csv
import io
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def export_plan(export_format, plan_data=None):
    OUTPUT_DIR.mkdir(exist_ok=True)
    if plan_data is None:
        plan_data = {}
    export_format = (export_format or "TXT").upper()
    file_name = f"output_plan.{export_format.lower()}"
    file_path = OUTPUT_DIR / file_name

    if export_format == "JSON":
        file_path.write_text(json.dumps(plan_data, indent=2), encoding="utf-8")
    elif export_format == "CSV":
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["field", "value"])
        for key, value in plan_data.items():
            if isinstance(value, dict):
                for result_key, result_value in value.items():
                    writer.writerow([f"{key}.{result_key}", result_value])
            else:
                writer.writerow([key, value])
        file_path.write_text(output.getvalue(), encoding="utf-8")
    else:
        payload = "\n".join(
            f"{key}: {json.dumps(value) if isinstance(value, dict) else value}"
            for key, value in plan_data.items()
        )
        file_path.write_text(payload or "No plan data available.", encoding="utf-8")

    return str(file_path)
