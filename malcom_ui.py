import tkinter as tk
from tkinter import ttk

from tkinterweb import HtmlFrame

from plan_schema import LEGACY_FIELD_ATTRIBUTES, PLAN_SECTIONS, REQUIRED_FIELD_KEYS


class StatusBar:
    def __init__(self, root):
        self.label = tk.Label(root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.label.pack(fill=tk.X, side=tk.BOTTOM)

    def set(self, message):
        self.label.config(text=message)

    def showMessage(self, message, timeout=None):
        self.label.config(text=message)


class Ui_MainWindow:
    def __init__(self):
        self.root = None
        self.loadWeightInput = None
        self.centerOfGravityInput = None
        self.equipmentSpecsInput = None
        self.environmentalConditionsInput = None
        self.loadFactorInput = None
        self.numberOfLegsInput = None
        self.slingAngleInput = None
        self.ratedCapacityInput = None
        self.resultsOutput = None
        self.exportFormatComboBox = None
        self.calculateButton = None
        self.documentationButton = None
        self.exportButton = None
        self.saveButton = None
        self.loadButton = None
        self.resetButton = None
        self.reportNotebook = None
        self.reportTab = None
        self.reportViewer = None
        self.printPlanButton = None
        self.aiTab = None
        self.aiProviderInput = None
        self.aiModelInput = None
        self.aiRefreshModelsButton = None
        self.aiOpenRouterKeyInput = None
        self.aiEndpointInput = None
        self.aiChatOutput = None
        self.aiPromptInput = None
        self.aiSendButton = None
        self.aiClearButton = None
        self.aiDiagramViewer = None
        self.aboutButton = None
        self.helpButton = None
        self.statusBar = None
        self.plan_fields = {}

    def setupUi(self, root):
        self.root = root
        root.title("MALCOM | Lift Planning Workspace")
        root.configure(background="#f2f5f3")

        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f2f5f3")
        style.configure("Panel.TLabelframe", background="#ffffff", bordercolor="#d6dfda")
        style.configure("Panel.TLabelframe.Label", background="#ffffff", foreground="#263b36", font=("Segoe UI", 10, "bold"))
        style.configure("TLabel", background="#f2f5f3", foreground="#263b36", font=("Segoe UI", 9))
        style.configure("Panel.TLabel", background="#ffffff")
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"), foreground="#183f36")
        style.configure("Subtle.TLabel", foreground="#60716b")
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 8))
        style.configure("TButton", padding=(10, 7))

        main_frame = ttk.Frame(root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=6)
        main_frame.columnconfigure(1, weight=5)
        main_frame.rowconfigure(1, weight=1)

        header = ttk.Frame(main_frame)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        ttk.Label(header, text="MALCOM", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Lift planning workspace", style="Subtle.TLabel").pack(anchor="w", pady=(2, 0))

        inputs = ttk.LabelFrame(main_frame, text="Lift plan intake", style="Panel.TLabelframe", padding=12)
        inputs.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        ttk.Label(
            inputs,
            text="Fields marked * are the baseline completion checklist. Enter N/A with a reason when not applicable; verify project and local requirements.",
            style="Subtle.TLabel",
            wraplength=440,
        ).pack(anchor="w", pady=(0, 10))

        notebook = ttk.Notebook(inputs)
        notebook.pack(fill=tk.BOTH, expand=True)
        for section_name, fields in PLAN_SECTIONS:
            page = ttk.Frame(notebook)
            notebook.add(page, text=section_name)
            canvas = tk.Canvas(page, background="#ffffff", highlightthickness=0)
            scrollbar = ttk.Scrollbar(page, orient=tk.VERTICAL, command=canvas.yview)
            canvas.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            form = ttk.Frame(canvas, padding=12)
            form.columnconfigure(0, weight=1)
            window_id = canvas.create_window((0, 0), window=form, anchor="nw")
            form.bind(
                "<Configure>",
                lambda _event, target=canvas: target.configure(scrollregion=target.bbox("all")),
            )
            canvas.bind(
                "<Configure>",
                lambda event, target=canvas, window=window_id: target.itemconfigure(window, width=event.width),
            )
            for row, (key, label) in enumerate(fields):
                field_label = f"{label} *" if key in REQUIRED_FIELD_KEYS else label
                ttk.Label(form, text=field_label, style="Panel.TLabel").grid(
                    row=row * 2, column=0, sticky="w", pady=(5, 2)
                )
                field = ttk.Entry(form)
                field.grid(row=row * 2 + 1, column=0, sticky="ew", pady=(0, 5))
                self.plan_fields[key] = field
                legacy_attribute = LEGACY_FIELD_ATTRIBUTES.get(key)
                if legacy_attribute:
                    setattr(self, legacy_attribute, field)

        output = ttk.LabelFrame(main_frame, text="Assessment and report", style="Panel.TLabelframe", padding=10)
        output.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
        output.rowconfigure(0, weight=1)
        output.columnconfigure(0, weight=1)
        self.reportNotebook = ttk.Notebook(output)
        self.reportNotebook.grid(row=0, column=0, sticky="nsew")

        assessment_tab = ttk.Frame(self.reportNotebook)
        self.reportTab = ttk.Frame(self.reportNotebook)
        self.aiTab = ttk.Frame(self.reportNotebook)
        self.reportNotebook.add(assessment_tab, text="Assessment")
        self.reportNotebook.add(self.reportTab, text="Plan report")
        self.reportNotebook.add(self.aiTab, text="AI diagram")
        assessment_tab.rowconfigure(0, weight=1)
        assessment_tab.columnconfigure(0, weight=1)
        self.resultsOutput = tk.Text(
            assessment_tab,
            height=18,
            wrap=tk.WORD,
            background="#ffffff",
            foreground="#263b36",
            relief=tk.FLAT,
            padx=10,
            pady=10,
            font=("Consolas", 10),
        )
        self.resultsOutput.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.resultsOutput.insert(
            tk.END,
            "Enter the lift and rigging data, then calculate to create a preliminary screening.\n\n"
            "This tool does not approve a lift. A competent person must verify the complete lift plan.",
        )
        self.resultsOutput.configure(state=tk.DISABLED)

        report_toolbar = ttk.Frame(self.reportTab, padding=(8, 8, 8, 4))
        report_toolbar.pack(fill=tk.X)
        self.printPlanButton = ttk.Button(report_toolbar, text="Print plan", state=tk.DISABLED)
        self.printPlanButton.pack(side=tk.RIGHT)
        self.reportViewer = HtmlFrame(
            self.reportTab,
            messages_enabled=False,
            javascript_enabled=False,
        )
        self.reportViewer.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.reportViewer.load_html(
            "<html><body style='font-family:Segoe UI,sans-serif;padding:24px;color:#263b36'>"
            "<h2>Plan report</h2><p>Generate a plan to preview it here.</p></body></html>"
        )

        ai_settings = ttk.Frame(self.aiTab, padding=(8, 8, 8, 4))
        ai_settings.pack(fill=tk.X)
        ai_settings.columnconfigure(3, weight=1)
        ttk.Label(ai_settings, text="Provider").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.aiProviderInput = ttk.Combobox(
            ai_settings,
            values=["OpenRouter API", "Ollama (local)", "OpenAI API"],
            state="readonly",
            width=16,
        )
        self.aiProviderInput.set("OpenRouter API")
        self.aiProviderInput.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        ttk.Label(ai_settings, text="Model").grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.aiModelInput = ttk.Combobox(ai_settings, state="readonly")
        self.aiModelInput.grid(row=0, column=3, sticky="ew")
        self.aiEndpointLabel = ttk.Label(ai_settings, text="Ollama URL")
        self.aiEndpointLabel.grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(6, 0))
        self.aiEndpointInput = ttk.Entry(ai_settings)
        self.aiEndpointInput.insert(0, "http://127.0.0.1:11434")
        self.aiEndpointInput.grid(row=1, column=1, columnspan=3, sticky="ew", pady=(6, 0))
        self.aiOpenRouterKeyLabel = ttk.Label(ai_settings, text="OpenRouter key")
        self.aiOpenRouterKeyLabel.grid(row=2, column=0, sticky="w", padx=(0, 5), pady=(6, 0))
        self.aiOpenRouterKeyInput = ttk.Entry(ai_settings, show="*")
        self.aiOpenRouterKeyInput.grid(row=2, column=1, columnspan=3, sticky="ew", pady=(6, 0))
        self.aiKeyHint = ttk.Label(ai_settings, text="Key is used for this session only; it is not saved.", style="Subtle.TLabel")
        self.aiKeyHint.grid(row=3, column=0, columnspan=3, sticky="w", pady=(6, 0))
        self.aiRefreshModelsButton = ttk.Button(ai_settings, text="Load free models")
        self.aiRefreshModelsButton.grid(row=3, column=3, sticky="e", pady=(6, 0))
        self.aiProviderInput.bind("<<ComboboxSelected>>", self._update_ai_provider)
        self.aiModelInput.bind("<<ComboboxSelected>>", self._update_ai_model_hint)
        self.aiModelInput.bind("<FocusOut>", self._update_ai_model_hint)

        ttk.Label(
            self.aiTab,
            text="Describe the operation; AI drafts scene labels and layout. The diagram is conceptual, not an engineered lift drawing.",
            style="Subtle.TLabel",
            wraplength=500,
        ).pack(fill=tk.X, padx=10, pady=(0, 5))

        ai_split = ttk.Panedwindow(self.aiTab, orient=tk.VERTICAL)
        ai_split.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        chat_panel = ttk.Frame(ai_split, padding=4)
        diagram_panel = ttk.Frame(ai_split, padding=4)
        ai_split.add(chat_panel, weight=1)
        ai_split.add(diagram_panel, weight=2)

        chat_panel.rowconfigure(0, weight=1)
        chat_panel.columnconfigure(0, weight=1)
        chat_scroll = ttk.Scrollbar(chat_panel, orient=tk.VERTICAL)
        chat_scroll.grid(row=0, column=1, sticky="ns")
        self.aiChatOutput = tk.Text(
            chat_panel,
            height=8,
            wrap=tk.WORD,
            background="#ffffff",
            foreground="#263b36",
            relief=tk.FLAT,
            padx=8,
            pady=8,
            yscrollcommand=chat_scroll.set,
        )
        self.aiChatOutput.grid(row=0, column=0, sticky="nsew")
        chat_scroll.configure(command=self.aiChatOutput.yview)
        self.aiChatOutput.insert(
            tk.END,
            "MALCOM AI: OpenRouter offers hosted :free models with an account key; use Load free models to list compatible choices. "
            "Ollama provides a private local option. Then describe the lift scene.\n\n"
            "Example: A shore-based mobile crane lifts a steel container from a vessel deck. Show two slings and label the vessel.",
        )
        self.aiChatOutput.configure(state=tk.DISABLED)

        ttk.Label(chat_panel, text="Describe or refine the scene").grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 3))
        self.aiPromptInput = tk.Text(chat_panel, height=3, wrap=tk.WORD)
        self.aiPromptInput.grid(row=2, column=0, columnspan=2, sticky="ew")
        chat_actions = ttk.Frame(chat_panel)
        chat_actions.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.aiSendButton = ttk.Button(chat_actions, text="Send and draw", style="Primary.TButton")
        self.aiSendButton.pack(side=tk.LEFT)
        self.aiClearButton = ttk.Button(chat_actions, text="Clear chat")
        self.aiClearButton.pack(side=tk.LEFT, padx=6)
        ttk.Label(chat_actions, text="AI scene assistant", style="Subtle.TLabel").pack(side=tk.RIGHT)

        diagram_panel.rowconfigure(0, weight=1)
        diagram_panel.columnconfigure(0, weight=1)
        self.aiDiagramViewer = tk.Canvas(
            diagram_panel,
            background="#07151b",
            highlightthickness=0,
        )
        self.aiDiagramViewer.grid(row=0, column=0, sticky="nsew")
        self.aiDiagramViewer.create_text(
            20,
            20,
            anchor="nw",
            text="The generated 2D scene will appear here.",
            fill="#9ab6b7",
            font=("Segoe UI", 12),
        )

        self._update_ai_provider()

        buttons = ttk.Frame(main_frame)
        buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        self.calculateButton = ttk.Button(buttons, text="Calculate screening", style="Primary.TButton")
        self.calculateButton.pack(side=tk.LEFT, padx=(0, 8))
        self.documentationButton = ttk.Button(buttons, text="Generate plan")
        self.documentationButton.pack(side=tk.LEFT, padx=4)
        self.exportButton = ttk.Button(buttons, text="Export")
        self.exportButton.pack(side=tk.LEFT, padx=4)
        self.saveButton = ttk.Button(buttons, text="Save inputs")
        self.saveButton.pack(side=tk.LEFT, padx=4)
        self.loadButton = ttk.Button(buttons, text="Load inputs")
        self.loadButton.pack(side=tk.LEFT, padx=4)
        self.resetButton = ttk.Button(buttons, text="Clear")
        self.resetButton.pack(side=tk.LEFT, padx=4)

        export_row = ttk.Frame(buttons)
        export_row.pack(side=tk.RIGHT)
        ttk.Label(export_row, text="Format:").pack(side=tk.LEFT, padx=(0, 8))
        self.exportFormatComboBox = ttk.Combobox(export_row, values=["TXT", "JSON", "CSV"], state="readonly")
        self.exportFormatComboBox.current(0)
        self.exportFormatComboBox.pack(side=tk.LEFT)

        self.statusBar = StatusBar(root)

    def _update_ai_provider(self, _event=None):
        provider = self.aiProviderInput.get()
        if provider == "OpenRouter API":
            self.aiEndpointInput.configure(state=tk.DISABLED)
            self.aiOpenRouterKeyInput.configure(state=tk.NORMAL)
            self.aiModelInput.configure(values=())
            if not self.aiModelInput.get().endswith(":free"):
                self.aiModelInput.set("")
            self.aiRefreshModelsButton.configure(state=tk.NORMAL)
            self.aiKeyHint.configure(
                text="Set OPENROUTER_API_KEY, then load the currently available :free models."
            )
        elif provider == "OpenAI API":
            self.aiEndpointInput.configure(state=tk.DISABLED)
            self.aiOpenRouterKeyInput.configure(state=tk.DISABLED)
            self.aiKeyHint.configure(text="Set OPENAI_API_KEY in the environment; never paste the key here.")
            self.aiModelInput.configure(values=["gpt-4.1-mini", "gpt-4o-mini"])
            if self.aiModelInput.get() not in self.aiModelInput.cget("values"):
                self.aiModelInput.set("gpt-4.1-mini")
            self.aiRefreshModelsButton.configure(state=tk.DISABLED)
        else:
            self.aiEndpointInput.configure(state=tk.NORMAL)
            self.aiOpenRouterKeyInput.configure(state=tk.DISABLED)
            local_models = ("qwen2.5:3b", "qwen2.5:7b", "llama3.2:3b", "gemma3:4b")
            self.aiModelInput.configure(values=local_models)
            if self.aiModelInput.get() not in local_models:
                self.aiModelInput.set(local_models[0])
            self.aiKeyHint.configure(
                text=f"Free, local model. Install Ollama, then run: ollama pull {self.aiModelInput.get()}"
            )
            self.aiRefreshModelsButton.configure(state=tk.DISABLED)

    def _update_ai_model_hint(self, _event=None):
        if self.aiProviderInput.get() == "Ollama (local)":
            self.aiKeyHint.configure(
                text=f"Free, local model. Install Ollama, then run: ollama pull {self.aiModelInput.get()}"
            )
