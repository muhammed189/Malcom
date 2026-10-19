import ast
import json
import os
import sys
import threading
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import tkinter as tk
from tkinter import messagebox

import malcom_ui
from documentation_generator import generate_plan
from export_formats import export_plan
from lifting_calculations import perform_calculations
from plan_schema import CALCULATION_FIELDS, get_missing_required_fields
from rigging_diagrams import generate_diagrams
from ai_diagram import draw_scene_on_canvas, fetch_openrouter_free_models


class MalcomApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MALCOM | Lift Planning Workspace")
        self.root.geometry("1080x1000")
        self.root.minsize(860, 1000)

        self.ui = malcom_ui.Ui_MainWindow()
        self.ui.setupUi(self.root)
        self.last_generated_plan_path = None
        self.last_ai_scene = None
        self.last_ai_diagram_path = None
        self.ai_messages = []
        self.ai_request_running = False
        self.ai_model_refresh_running = False

        self.ui.calculateButton.configure(command=self.calculate_lift)
        self.ui.documentationButton.configure(command=self.generate_documentation)
        self.ui.exportButton.configure(command=self.export_plan)
        self.ui.saveButton.configure(command=self.save_configuration)
        self.ui.loadButton.configure(command=self.load_configuration)
        self.ui.resetButton.configure(command=self.reset_inputs)
        self.ui.printPlanButton.configure(command=self.print_plan)
        self.ui.aiSendButton.configure(command=self.generate_ai_diagram)
        self.ui.aiClearButton.configure(command=self.clear_ai_chat)
        self.ui.aiRefreshModelsButton.configure(command=self.refresh_openrouter_models)

        self.root.protocol("WM_DELETE_WINDOW", self.exit_application)

    def _get_plan_data(self):
        return {key: field.get().strip() for key, field in self.ui.plan_fields.items()}

    def _get_assessed_plan(self):
        plan_data = self._get_plan_data()
        calculation_inputs = {key: plan_data[key] for key in CALCULATION_FIELDS}
        results = perform_calculations(**calculation_inputs)
        plan_data["calculation_results"] = results
        missing_fields = get_missing_required_fields(plan_data)
        plan_data["intake_completeness"] = {
            "status": "INCOMPLETE DRAFT" if missing_fields else "CORE INTAKE COMPLETE - REVIEW REQUIRED",
            "missing_count": len(missing_fields),
            "missing_fields": missing_fields,
        }
        return plan_data, results

    def _display_results(self, results, completeness):
        lines = [
            "PRELIMINARY SCREENING",
            "",
            f"Intake status:           {completeness['status']}",
            f"Baseline items missing:  {completeness['missing_count']}",
            "",
            f"Estimated load per leg: {results['estimated_leg_load_t']:.3f} t",
            f"Entered WLL per leg:    {results['rated_capacity_per_leg_t']:.3f} t",
            f"WLL utilization:        {results['utilization_percent']:.1f}%",
            f"Capacity check:         {results['capacity_check']}",
            "",
            results["status"],
            "",
            results["limitations"],
        ]
        self.ui.resultsOutput.configure(state=tk.NORMAL)
        self.ui.resultsOutput.delete("1.0", tk.END)
        self.ui.resultsOutput.insert(tk.END, "\n".join(lines))
        self.ui.resultsOutput.configure(state=tk.DISABLED)

    def calculate_lift(self):
        try:
            plan_data, results = self._get_assessed_plan()
            completeness = plan_data["intake_completeness"]
            self._display_results(results, completeness)
            self.ui.statusBar.set(
                f"{results['capacity_check']} | {completeness['missing_count']} baseline items missing | review required"
            )
        except ValueError as exc:
            messagebox.showerror("Input Error", str(exc))
            self.ui.statusBar.set("Invalid input")

    def generate_documentation(self):
        try:
            plan_data, results = self._get_assessed_plan()
            if self.last_ai_scene:
                plan_data["ai_scene"] = self.last_ai_scene
            output_path = generate_plan(plan_data)
            self.last_generated_plan_path = Path(output_path)
            self.ui.reportViewer.load_file(str(self.last_generated_plan_path.resolve()))
            self.ui.reportNotebook.select(self.ui.reportTab)
            self.ui.printPlanButton.configure(state=tk.NORMAL)
            completeness = plan_data["intake_completeness"]
            self._display_results(results, completeness)
            self.ui.statusBar.set(
                f"Draft saved; {completeness['missing_count']} baseline items missing: {output_path}"
            )
        except Exception as exc:  # pragma: no cover - GUI safety net
            messagebox.showerror("Document Error", str(exc))
            self.ui.statusBar.set("Documentation failed")

    def print_plan(self):
        if not self.last_generated_plan_path or not self.last_generated_plan_path.exists():
            messagebox.showinfo("Print Plan", "Generate a plan before printing.")
            return

        report_path = self.last_generated_plan_path.resolve()
        try:
            os.startfile(str(report_path), "print")
            self.ui.statusBar.set("Print request sent to the default HTML handler")
        except (AttributeError, OSError):
            try:
                os.startfile(str(report_path))
            except (AttributeError, OSError) as exc:
                messagebox.showerror("Print Error", str(exc))
                self.ui.statusBar.set("Could not open the plan for printing")
                return
            messagebox.showinfo(
                "Print Plan",
                "The plan is open in your browser. Choose Print from the browser menu to print a hard copy.",
            )
            self.ui.statusBar.set("Plan opened in browser for printing")

    def _append_ai_message(self, speaker, text):
        self.ui.aiChatOutput.configure(state=tk.NORMAL)
        self.ui.aiChatOutput.insert(tk.END, f"{speaker}: {text}\n\n")
        self.ui.aiChatOutput.see(tk.END)
        self.ui.aiChatOutput.configure(state=tk.DISABLED)

    def generate_ai_diagram(self):
        if self.ai_request_running:
            return
        prompt = self.ui.aiPromptInput.get("1.0", tk.END).strip()
        if not prompt:
            self.ui.statusBar.set("Describe the lift scene before sending")
            return

        model = self.ui.aiModelInput.get().strip()
        provider = self.ui.aiProviderInput.get()
        endpoint = self.ui.aiEndpointInput.get().strip()
        api_key = self.ui.aiOpenRouterKeyInput.get().strip() if provider == "OpenRouter API" else ""
        plan_data = self._get_plan_data()
        history = list(self.ai_messages)
        self.ai_request_running = True
        self.ui.aiSendButton.configure(state=tk.DISABLED)
        self.ui.aiPromptInput.delete("1.0", tk.END)
        self._append_ai_message("YOU", prompt)
        self._append_ai_message("MALCOM AI", "Working on a conceptual 2D scene...")
        self.ui.statusBar.set(f"Requesting a scene from {model or 'the selected model'}...")

        worker = threading.Thread(
            target=self._run_ai_diagram,
            args=(prompt, plan_data, history, endpoint, model, provider, api_key),
            daemon=True,
        )
        worker.start()

    def refresh_openrouter_models(self):
        if self.ai_model_refresh_running:
            return
        if self.ui.aiProviderInput.get() != "OpenRouter API":
            self.ui.statusBar.set("Select OpenRouter API to load its free models")
            return

        self.ai_model_refresh_running = True
        self.ui.aiRefreshModelsButton.configure(state=tk.DISABLED)
        self.ui.aiKeyHint.configure(text="Fetching OpenRouter models that advertise structured JSON output...")
        worker = threading.Thread(target=self._load_openrouter_models, daemon=True)
        worker.start()

    def _load_openrouter_models(self):
        try:
            models = fetch_openrouter_free_models()
        except Exception as exc:
            error = str(exc)
            self.root.after(0, self._finish_openrouter_models, None, error)
            return
        self.root.after(0, self._finish_openrouter_models, models, None)

    def _finish_openrouter_models(self, models, error):
        if not self.root.winfo_exists():
            return
        self.ai_model_refresh_running = False
        if self.ui.aiProviderInput.get() != "OpenRouter API":
            return
        self.ui.aiRefreshModelsButton.configure(state=tk.NORMAL)
        if error:
            self.ui.aiKeyHint.configure(text=f"Could not load free models: {error}")
            self.ui.statusBar.set("OpenRouter model list unavailable")
            return

        previous_model = self.ui.aiModelInput.get()
        self.ui.aiModelInput.configure(values=models)
        self.ui.aiModelInput.set(previous_model if previous_model in models else models[0])
        self.ui.aiKeyHint.configure(
            text=f"Loaded {len(models)} :free models. Set OPENROUTER_API_KEY before sending a prompt."
        )
        self.ui.statusBar.set(f"Loaded {len(models)} OpenRouter free models")

    def _run_ai_diagram(self, prompt, plan_data, history, endpoint, model, provider, api_key):
        try:
            diagram_path, scene, user_content = generate_diagrams(
                prompt,
                plan_data,
                history,
                endpoint,
                model,
                provider,
                api_key,
            )
        except Exception as exc:
            error = str(exc)
            self.root.after(0, self._finish_ai_diagram, None, None, None, error)
            return
        self.root.after(0, self._finish_ai_diagram, scene, user_content, diagram_path, None)

    def _finish_ai_diagram(self, scene, user_content, diagram_path, error):
        if not self.root.winfo_exists():
            return
        self.ai_request_running = False
        self.ui.aiSendButton.configure(state=tk.NORMAL)

        if error:
            self._append_ai_message("MALCOM AI", f"Could not generate the scene: {error}")
            self.ui.statusBar.set("AI diagram request failed")
            return

        self.ai_messages.extend([
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": json.dumps(scene, ensure_ascii=True)},
        ])
        self.last_ai_scene = scene
        self.last_ai_diagram_path = Path(diagram_path)
        notes = "\n".join(f"- {note}" for note in scene["notes"]) or "- No additional assumptions noted."
        self._append_ai_message(
            "MALCOM AI",
            f"Drew: {scene['title']}\nLoad: {scene['load_label']} ({scene['load_kind']})\n"
            f"Crane: {scene['crane_location']}; illustrative boom angle {scene['boom_angle_degrees']:.0f}°\n"
            f"Vessel shown: {'yes' if scene['vessel_in_scene'] else 'no'}\n{notes}",
        )
        self.ui.reportNotebook.select(self.ui.aiTab)
        self.root.update_idletasks()
        draw_scene_on_canvas(self.ui.aiDiagramViewer, scene)
        self.ui.statusBar.set(f"Conceptual diagram generated with {self.ui.aiProviderInput.get()}: {diagram_path}")

    def clear_ai_chat(self):
        if self.ai_request_running:
            self.ui.statusBar.set("Wait for the current diagram request to finish")
            return
        self.ai_messages.clear()
        self.ui.aiChatOutput.configure(state=tk.NORMAL)
        self.ui.aiChatOutput.delete("1.0", tk.END)
        self.ui.aiChatOutput.insert(
            tk.END,
            "MALCOM AI: Describe the operation. Follow-up messages refine the last scene.\n\n",
        )
        self.ui.aiChatOutput.configure(state=tk.DISABLED)

    def export_plan(self):
        try:
            plan_data, results = self._get_assessed_plan()
            export_format = self.ui.exportFormatComboBox.get()
            output_path = export_plan(export_format, plan_data)
            completeness = plan_data["intake_completeness"]
            self._display_results(results, completeness)
            self.ui.statusBar.set(
                f"Exported {export_format}; {completeness['missing_count']} baseline items missing: {output_path}"
            )
        except Exception as exc:  # pragma: no cover - GUI safety net
            messagebox.showerror("Export Error", str(exc))
            self.ui.statusBar.set("Export failed")

    def save_configuration(self):
        try:
            plan_data = self._get_plan_data()
            save_path = ROOT_DIR / "config.json"
            save_path.write_text(json.dumps(plan_data, indent=2), encoding="utf-8")
            self.ui.statusBar.set(f"Configuration saved to {save_path}")
        except Exception as exc:  # pragma: no cover - GUI safety net
            messagebox.showerror("Save Error", str(exc))
            self.ui.statusBar.set("Save failed")

    def load_configuration(self, path=None):
        try:
            config_path = Path(path) if path else ROOT_DIR / "config.json"
            if not config_path.exists():
                self.ui.statusBar.set("No saved configuration found")
                return
            content = config_path.read_text(encoding="utf-8")
            try:
                payload = json.loads(content)
            except json.JSONDecodeError:
                payload = ast.literal_eval(content)
            if not isinstance(payload, dict):
                raise ValueError("Configuration must contain a JSON object.")
            for key, field in self.ui.plan_fields.items():
                field.delete(0, tk.END)
                field.insert(0, str(payload.get(key, "")))
            self.ui.statusBar.set("Configuration loaded")
        except Exception as exc:  # pragma: no cover - GUI safety net
            messagebox.showerror("Load Error", str(exc))
            self.ui.statusBar.set("Load failed")

    def reset_inputs(self):
        for field in self.ui.plan_fields.values():
            field.delete(0, tk.END)
        self.ui.resultsOutput.configure(state=tk.NORMAL)
        self.ui.resultsOutput.delete("1.0", tk.END)
        self.ui.resultsOutput.configure(state=tk.DISABLED)
        self.ui.statusBar.set("Inputs cleared")

    def exit_application(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    app = MalcomApp()
    app.run()


if __name__ == "__main__":
    main()

