import html
import ipaddress
import json
import math
import os
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit


OUTPUT_DIR = Path(__file__).resolve().parent / "output"

SCENE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "load_label": {"type": "string"},
        "load_kind": {"type": "string", "enum": ["cargo", "container", "vehicle", "vessel", "unknown"]},
        "vessel_in_scene": {"type": "boolean"},
        "crane_location": {"type": "string", "enum": ["shore", "vessel"]},
        "boom_angle_degrees": {"type": "number", "minimum": 15, "maximum": 75},
        "rigging_legs": {"type": "integer", "minimum": 1, "maximum": 4},
        "notes": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
    },
    "required": [
        "title",
        "load_label",
        "load_kind",
        "vessel_in_scene",
        "crane_location",
        "boom_angle_degrees",
        "rigging_legs",
        "notes",
    ],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You create conceptual 2D lifting-operation scene descriptions for a safety-critical planning application.
Return only the requested JSON object matching the supplied schema. Do not provide safety approval, capacity conclusions, or calculations.
Use only facts explicitly supplied by the user or plan data. If an illustrative boom angle is not supplied, choose a reasonable visual angle and add a note that it is illustrative.
Set vessel_in_scene when the description includes a ship or vessel as part of the scene. Set crane_location to shore or vessel based on the description; if unclear, use shore and add a note that placement is assumed.
Choose load_kind and a short load_label from the description. Never invent load dimensions, weight, lifting-point ratings, crane capacity, or rigging suitability. Put missing visual assumptions in notes.
The diagram renderer is schematic and not to scale. All returned scene data is for illustration only."""


def _validate_scene(scene):
    if not isinstance(scene, dict) or set(scene) != set(SCENE_SCHEMA["required"]):
        raise ValueError("The AI response did not match the required scene format. Try a simpler description.")

    if not isinstance(scene["load_kind"], str) or not isinstance(scene["crane_location"], str):
        raise ValueError("The AI returned invalid scene categories.")
    allowed_kinds = {"cargo", "container", "vehicle", "vessel", "unknown"}
    if scene["load_kind"] not in allowed_kinds:
        raise ValueError("The AI returned an unsupported load type.")
    if scene["crane_location"] not in {"shore", "vessel"}:
        raise ValueError("The AI returned an unsupported crane location.")
    if type(scene["vessel_in_scene"]) is not bool:
        raise ValueError("The AI returned an invalid vessel setting.")
    if not isinstance(scene["title"], str) or not isinstance(scene["load_label"], str):
        raise ValueError("The AI returned invalid scene labels.")
    if type(scene["rigging_legs"]) is not int or not 1 <= scene["rigging_legs"] <= 4:
        raise ValueError("The AI returned an invalid rigging-leg count.")
    try:
        angle = float(scene["boom_angle_degrees"])
    except (TypeError, ValueError) as exc:
        raise ValueError("The AI returned an invalid illustrative boom angle.") from exc
    if not math.isfinite(angle) or not 15 <= angle <= 75:
        raise ValueError("The AI returned an out-of-range illustrative boom angle.")
    if not isinstance(scene["notes"], list) or len(scene["notes"]) > 4:
        raise ValueError("The AI returned invalid scene notes.")
    if not all(isinstance(note, str) for note in scene["notes"]):
        raise ValueError("The AI returned invalid scene notes.")

    scene["title"] = str(scene["title"]).strip()[:100] or "Lift operation"
    scene["load_label"] = str(scene["load_label"]).strip()[:60] or "Load"
    scene["boom_angle_degrees"] = angle
    scene["notes"] = [note.strip()[:180] for note in scene["notes"]]
    return scene


def _scene_messages(prompt, plan_data, history):
    supplied_data = {key: value for key, value in plan_data.items() if str(value).strip()}
    user_content = (
        f"Operation description:\n{prompt.strip()}\n\n"
        f"Entered lift-plan fields (reference only; do not infer missing values):\n"
        f"{json.dumps(supplied_data, ensure_ascii=True)}"
    )
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history[-8:])
    messages.append({"role": "user", "content": user_content})
    return messages, user_content


def _read_response(request, timeout):
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"AI service returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("Could not reach the selected AI service. Check your connection and try again.") from exc


def _parse_scene(content, provider_name):
    try:
        return _validate_scene(json.loads(content))
    except (TypeError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"{provider_name} returned an unreadable or invalid scene. Try again.") from exc


def _request_openai_scene(messages, model, timeout):
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add your OpenAI API key to the environment, then restart MALCOM."
        )
    payload = {
        "model": model,
        "messages": messages,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "lift_scene",
                "strict": True,
                "schema": SCENE_SCHEMA,
            },
        },
        "temperature": 0.2,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    response_data = _read_response(request, timeout)
    try:
        message = response_data["choices"][0]["message"]
        if message.get("refusal"):
            raise RuntimeError(f"OpenAI declined the scene request: {message['refusal'][:300]}")
        return _parse_scene(message["content"], "OpenAI")
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("OpenAI returned an unexpected response. Check the selected model and try again.") from exc


def fetch_openrouter_free_models(timeout=30):
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers={"Accept": "application/json"},
        method="GET",
    )
    response_data = _read_response(request, timeout)
    models = response_data.get("data", [])
    free_models = [
        model["id"]
        for model in models
        if isinstance(model, dict)
        and isinstance(model.get("id"), str)
        and model["id"].endswith(":free")
        and isinstance(model.get("supported_parameters"), list)
        and "structured_outputs" in model["supported_parameters"]
    ]
    if not free_models:
        raise RuntimeError("OpenRouter returned no free models that support structured JSON output.")
    return sorted(set(free_models))


def _request_openrouter_scene(messages, model, api_key, timeout):
    if not model.endswith(":free"):
        raise ValueError("Choose an OpenRouter model ending in :free to use the free-model provider.")
    api_key = api_key.strip()
    if not api_key:
        raise RuntimeError("Enter your OpenRouter API key in the AI tab before sending a prompt.")

    payload = {
        "model": model,
        "messages": messages,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "lift_scene",
                "strict": True,
                "schema": SCENE_SCHEMA,
            },
        },
        "provider": {"require_parameters": True},
        "temperature": 0.2,
    }
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    response_data = _read_response(request, timeout)
    try:
        message = response_data["choices"][0]["message"]
        if message.get("refusal"):
            raise RuntimeError(f"OpenRouter model declined the scene request: {message['refusal'][:300]}")
        return _parse_scene(message["content"], "OpenRouter")
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("OpenRouter returned an unexpected response. Check the model and try again.") from exc


def _request_ollama_scene(messages, endpoint, model, timeout):
    endpoint = endpoint.strip().rstrip("/")
    parsed_endpoint = urlsplit(endpoint)
    if parsed_endpoint.scheme != "http" or not parsed_endpoint.hostname:
        raise ValueError("Enter a local Ollama URL, such as http://127.0.0.1:11434.")
    if parsed_endpoint.username or parsed_endpoint.password:
        raise ValueError("Do not include credentials in the Ollama URL.")
    hostname = parsed_endpoint.hostname.lower()
    try:
        is_loopback = hostname == "localhost" or ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        is_loopback = False
    if not is_loopback:
        raise ValueError("For privacy, MALCOM only sends lift data to a local Ollama endpoint.")

    payload = {
        "model": model,
        "messages": messages,
        "format": SCENE_SCHEMA,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    request = urllib.request.Request(
        f"{endpoint}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        response_data = _read_response(request, timeout)
        content = response_data["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError("Ollama returned an unexpected response. Try again or select another model.") from exc
    return _parse_scene(content, "Ollama")


def request_scene(
    prompt,
    plan_data,
    history,
    endpoint,
    model,
    provider="Ollama (local)",
    api_key="",
    timeout=120,
):
    if not prompt.strip():
        raise ValueError("Describe the lifting operation first.")
    if not model.strip():
        raise ValueError("Enter a model name.")
    if not isinstance(plan_data, dict) or not isinstance(history, list):
        raise ValueError("Lift data or chat history is invalid.")

    messages, user_content = _scene_messages(prompt, plan_data, history)
    if provider == "OpenAI API":
        scene = _request_openai_scene(messages, model.strip(), timeout)
    elif provider == "OpenRouter API":
        scene = _request_openrouter_scene(messages, model.strip(), api_key, timeout)
    elif provider == "Ollama (local)":
        scene = _request_ollama_scene(messages, endpoint, model.strip(), timeout)
    else:
        raise ValueError("Choose OpenRouter API, OpenAI API, or Ollama (local).")
    return scene, user_content


def _vessel_svg():
    return '''
    <path d="M515 390 H895 L850 470 H575 Z" fill="#426f78" stroke="#b1d8ce" stroke-width="4"/>
    <path d="M555 390 L580 350 H675 L702 390 M710 390 L735 362 H822 L845 390" fill="#193a45" stroke="#8ebbb2" stroke-width="3"/>
    <path d="M578 414 H866 M590 437 H852" stroke="#79aaa7" stroke-width="2"/>
    <path d="M505 487 Q540 475 575 487 T645 487 T715 487 T785 487 T855 487 T925 487" fill="none" stroke="#4bb9ad" stroke-width="3"/>
    <text x="684" y="460" fill="#e5eee5" font-size="17" font-family="Segoe UI, sans-serif">VESSEL / DECK</text>
    '''


def render_scene_svg(scene):
    scene = _validate_scene(dict(scene))
    vessel = _vessel_svg() if scene["vessel_in_scene"] else ""
    on_vessel = scene["crane_location"] == "vessel"
    base_x, base_y = (730, 388) if on_vessel else (145, 420)
    boom_direction = -1 if on_vessel else 1
    boom_length = 330
    angle = math.radians(scene["boom_angle_degrees"])
    tip_x = base_x + boom_direction * boom_length * math.cos(angle)
    tip_y = base_y - boom_length * math.sin(angle)
    load_center_x = tip_x
    load_top_y = max(205, min(320, tip_y + 112))
    half_width = 62 if scene["load_kind"] != "vessel" else 82
    load_bottom_y = load_top_y + 58
    hook_y = load_top_y - 38
    label = html.escape(scene["load_label"], quote=True)
    title = html.escape(scene["title"], quote=True)
    load_x = load_center_x - half_width

    if scene["load_kind"] == "vessel":
        load_shape = (
            f'<path d="M{load_x-14} {load_top_y+12} H{load_x+half_width+14} '
            f'L{load_x+half_width} {load_bottom_y} H{load_x-44} Z" '
            'fill="#9baeb0" stroke="#e0e9df" stroke-width="3"/>'
        )
    elif scene["load_kind"] == "vehicle":
        load_shape = (
            f'<path d="M{load_x+8} {load_top_y+35} L{load_x+22} {load_top_y+12} '
            f'H{load_x+half_width-12} L{load_x+half_width+5} {load_top_y+35} '
            f'V{load_bottom_y} H{load_x+8} Z" fill="#dcad42" stroke="#ffe184" stroke-width="3"/>'
        )
    else:
        load_shape = (
            f'<rect x="{load_x}" y="{load_top_y}" width="{half_width*2}" height="58" '
            'rx="2" fill="#d7ad49" stroke="#ffe184" stroke-width="3"/>'
        )
        if scene["load_kind"] == "container":
            load_shape += "".join(
                f'<path d="M{x} {load_top_y+5} V{load_bottom_y-5}" stroke="#8e7038" stroke-width="2"/>'
                for x in range(int(load_x + 13), int(load_x + half_width * 2), 15)
            )

    rigging_lines = []
    for index in range(scene["rigging_legs"]):
        fraction = (index + 1) / (scene["rigging_legs"] + 1)
        end_x = load_x + (half_width * 2 * fraction)
        rigging_lines.append(
            f'<path d="M{tip_x} {hook_y} L{end_x} {load_top_y+2}" '
            'stroke="#72d6c3" stroke-width="2"/>'
        )
    rigging_svg = "".join(rigging_lines)

    crane = f'''
    <g aria-label="Indicative crane">
      <path d="M{base_x-66} {base_y-40} H{base_x+61} L{base_x+82} {base_y-7} H{base_x-78} Z" fill="#dba52e" stroke="#f5cf64" stroke-width="3"/>
      <path d="M{base_x-47} {base_y-80} H{base_x+7} L{base_x+47} {base_y-40} H{base_x-47} Z" fill="#e8b333" stroke="#f5cf64" stroke-width="3"/>
      <path d="M{base_x-37} {base_y-72} H{base_x-3} V{base_y-45} H{base_x-37} Z" fill="#193b45" stroke="#8ab9b0" stroke-width="2"/>
      <path d="M{base_x+5} {base_y-72} H{base_x+22} L{base_x+38} {base_y-45} H{base_x+5} Z" fill="#193b45" stroke="#8ab9b0" stroke-width="2"/>
      <path d="M{base_x-16} {base_y-34} L{tip_x-10} {tip_y} L{tip_x+10} {tip_y} L{base_x+10} {base_y-34} Z" fill="#f3c54c" stroke="#ffe184" stroke-width="3"/>
      <path d="M{base_x-5} {base_y-38} L{tip_x} {tip_y+2}" stroke="#fff0ae" stroke-width="2"/>
      <circle cx="{base_x}" cy="{base_y-34}" r="11" fill="#254851" stroke="#ffdc69" stroke-width="4"/>
      <circle cx="{base_x-42}" cy="{base_y-1}" r="17" fill="#122a32" stroke="#b9c8bd" stroke-width="4"/>
      <circle cx="{base_x+44}" cy="{base_y-1}" r="17" fill="#122a32" stroke="#b9c8bd" stroke-width="4"/>
    </g>
    '''
    notes = " ".join(html.escape(note, quote=True) for note in scene["notes"])

    return f'''<svg xmlns="http://www.w3.org/2000/svg" class="crane-drawing" viewBox="0 0 1000 560" role="img" aria-label="Conceptual 2D lift operation schematic">
      <defs><pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="#123e49" stroke-width="1"/></pattern></defs>
      <rect width="1000" height="560" fill="#07151b"/><rect width="1000" height="560" fill="url(#grid)"/>
      <text x="32" y="42" fill="#66d4c0" font-size="19" font-weight="700" font-family="Segoe UI,sans-serif">{title}</text>
      <path d="M35 470 H965" stroke="#85b7b2" stroke-width="3"/>
      {vessel}
      {crane}
      <path d="M{tip_x} {tip_y} V{hook_y}" stroke="#d6e3d8" stroke-width="3"/>
      <path d="M{tip_x-10} {hook_y} Q{tip_x} {hook_y+13} {tip_x+10} {hook_y}" fill="none" stroke="#d6e3d8" stroke-width="3"/>
      {rigging_svg}
      {load_shape}
      <text x="{load_center_x}" y="{load_bottom_y+23}" fill="#e9f0e8" text-anchor="middle" font-size="15" font-family="Segoe UI,sans-serif">{label}</text>
      <text x="38" y="520" fill="#9ab6b7" font-size="13" font-family="Segoe UI,sans-serif">BOOM ANGLE (ILLUSTRATIVE): {scene['boom_angle_degrees']:.0f}°  |  RIGGING LEGS SHOWN: {scene['rigging_legs']}</text>
      <text x="38" y="542" fill="#ffca9d" font-size="12" font-family="Segoe UI,sans-serif">CONCEPTUAL ONLY / NOT TO SCALE / NOT FOR LIFT EXECUTION</text>
      <text x="520" y="542" fill="#9ab6b7" font-size="11" font-family="Segoe UI,sans-serif">{notes}</text>
    </svg>'''


def draw_scene_on_canvas(canvas, scene=None):
    if scene is not None:
        canvas.ai_scene = _validate_scene(dict(scene))
        if not getattr(canvas, "_scene_resize_bound", False):
            canvas.bind(
                "<Configure>",
                lambda event: draw_scene_on_canvas(event.widget),
                add="+",
            )
            canvas._scene_resize_bound = True

    scene = getattr(canvas, "ai_scene", None)
    canvas.delete("all")
    width = max(canvas.winfo_width(), 1)
    height = max(canvas.winfo_height(), 1)
    canvas.create_rectangle(0, 0, width, height, fill="#07151b", outline="")
    if not scene:
        canvas.create_text(
            24,
            24,
            anchor="nw",
            text="The generated 2D scene will appear here.",
            fill="#9ab6b7",
            font=("Segoe UI", 12),
        )
        return

    scale = min((width - 24) / 1000, (height - 24) / 560)
    if scale <= 0:
        return
    offset_x = (width - 1000 * scale) / 2
    offset_y = (height - 560 * scale) / 2

    def px(x):
        return offset_x + x * scale

    def py(y):
        return offset_y + y * scale

    text_size = max(7, round(13 * scale))
    title_size = max(10, round(19 * scale))
    for x in range(0, 1001, 32):
        canvas.create_line(px(x), py(0), px(x), py(560), fill="#123e49", width=1)
    for y in range(0, 561, 32):
        canvas.create_line(px(0), py(y), px(1000), py(y), fill="#123e49", width=1)

    canvas.create_text(
        px(32),
        py(42),
        anchor="w",
        text=scene["title"],
        fill="#66d4c0",
        font=("Segoe UI", title_size, "bold"),
    )
    canvas.create_line(px(35), py(470), px(965), py(470), fill="#85b7b2", width=max(2, round(3 * scale)))

    if scene["vessel_in_scene"]:
        canvas.create_polygon(
            px(515), py(390), px(895), py(390), px(850), py(470), px(575), py(470),
            fill="#426f78", outline="#b1d8ce", width=max(1, round(3 * scale)),
        )
        canvas.create_polygon(
            px(555), py(390), px(580), py(350), px(675), py(350), px(702), py(390),
            px(710), py(390), px(735), py(362), px(822), py(362), px(845), py(390),
            fill="#193a45", outline="#8ebbb2", width=max(1, round(2 * scale)),
        )
        canvas.create_line(px(578), py(414), px(866), py(414), fill="#79aaa7", width=max(1, round(2 * scale)))
        canvas.create_line(px(590), py(437), px(852), py(437), fill="#79aaa7", width=max(1, round(2 * scale)))
        water_points = []
        for x in range(505, 926, 12):
            water_points.extend((px(x), py(487 + 7 * math.sin(x / 20))))
        canvas.create_line(*water_points, fill="#4bb9ad", width=max(1, round(2 * scale)), smooth=True)
        canvas.create_text(
            px(684), py(460), text="VESSEL / DECK", fill="#e5eee5",
            font=("Segoe UI", text_size, "bold"),
        )

    on_vessel = scene["crane_location"] == "vessel"
    base_x, base_y = (730, 388) if on_vessel else (145, 420)
    boom_direction = -1 if on_vessel else 1
    boom_length = 330
    angle = math.radians(scene["boom_angle_degrees"])
    tip_x = base_x + boom_direction * boom_length * math.cos(angle)
    tip_y = base_y - boom_length * math.sin(angle)
    load_center_x = tip_x
    load_top_y = max(205, min(320, tip_y + 112))
    half_width = 82 if scene["load_kind"] == "vessel" else 62
    load_bottom_y = load_top_y + 58
    load_x = load_center_x - half_width
    hook_y = load_top_y - 38

    canvas.create_polygon(
        px(base_x - 66), py(base_y - 40), px(base_x + 61), py(base_y - 40),
        px(base_x + 82), py(base_y - 7), px(base_x - 78), py(base_y - 7),
        fill="#dba52e", outline="#f5cf64", width=max(1, round(3 * scale)),
    )
    canvas.create_polygon(
        px(base_x - 47), py(base_y - 80), px(base_x + 7), py(base_y - 80),
        px(base_x + 47), py(base_y - 40), px(base_x - 47), py(base_y - 40),
        fill="#e8b333", outline="#f5cf64", width=max(1, round(3 * scale)),
    )
    canvas.create_polygon(
        px(base_x - 37), py(base_y - 72), px(base_x - 3), py(base_y - 72),
        px(base_x - 3), py(base_y - 45), px(base_x - 37), py(base_y - 45),
        fill="#193b45", outline="#8ab9b0", width=max(1, round(2 * scale)),
    )
    canvas.create_line(
        px(base_x), py(base_y - 34), px(tip_x), py(tip_y),
        fill="#f3c54c", width=max(5, round(18 * scale)),
    )
    canvas.create_line(
        px(base_x - 5), py(base_y - 38), px(tip_x), py(tip_y + 2),
        fill="#fff0ae", width=max(1, round(2 * scale)),
    )
    canvas.create_oval(
        px(base_x - 42), py(base_y - 18), px(base_x - 8), py(base_y + 16),
        fill="#122a32", outline="#b9c8bd", width=max(1, round(4 * scale)),
    )
    canvas.create_oval(
        px(base_x + 27), py(base_y - 18), px(base_x + 61), py(base_y + 16),
        fill="#122a32", outline="#b9c8bd", width=max(1, round(4 * scale)),
    )
    canvas.create_line(px(tip_x), py(tip_y), px(tip_x), py(hook_y), fill="#d6e3d8", width=max(1, round(3 * scale)))
    canvas.create_arc(
        px(tip_x - 10), py(hook_y - 8), px(tip_x + 10), py(hook_y + 8),
        start=205, extent=130, style="arc", outline="#d6e3d8", width=max(1, round(3 * scale)),
    )

    load_fill = "#9baeb0" if scene["load_kind"] == "vessel" else "#d7ad49"
    load_outline = "#e0e9df" if scene["load_kind"] == "vessel" else "#ffe184"
    for index in range(scene["rigging_legs"]):
        fraction = (index + 1) / (scene["rigging_legs"] + 1)
        end_x = load_x + 2 * half_width * fraction
        canvas.create_line(
            px(tip_x), py(hook_y), px(end_x), py(load_top_y + 2),
            fill="#72d6c3", width=max(1, round(2 * scale)),
        )

    if scene["load_kind"] == "vessel":
        canvas.create_polygon(
            px(load_x - 14), py(load_top_y + 12), px(load_x + half_width + 14), py(load_top_y + 12),
            px(load_x + half_width), py(load_bottom_y), px(load_x - 44), py(load_bottom_y),
            fill=load_fill, outline=load_outline, width=max(1, round(3 * scale)),
        )
    elif scene["load_kind"] == "vehicle":
        canvas.create_polygon(
            px(load_x + 8), py(load_top_y + 35), px(load_x + 22), py(load_top_y + 12),
            px(load_x + half_width - 12), py(load_top_y + 12), px(load_x + half_width + 5), py(load_top_y + 35),
            px(load_x + half_width + 5), py(load_bottom_y), px(load_x + 8), py(load_bottom_y),
            fill="#dcad42", outline="#ffe184", width=max(1, round(3 * scale)),
        )
    else:
        canvas.create_rectangle(
            px(load_x), py(load_top_y), px(load_x + 2 * half_width), py(load_bottom_y),
            fill=load_fill, outline=load_outline, width=max(1, round(3 * scale)),
        )
        if scene["load_kind"] == "container":
            for x in range(int(load_x + 13), int(load_x + 2 * half_width), 15):
                canvas.create_line(
                    px(x), py(load_top_y + 5), px(x), py(load_bottom_y - 5),
                    fill="#8e7038", width=max(1, round(2 * scale)),
                )

    canvas.create_text(
        px(load_center_x), py(load_bottom_y + 20), text=scene["load_label"],
        fill="#e9f0e8", font=("Segoe UI", text_size),
    )
    canvas.create_text(
        px(35), py(520), anchor="w",
        text=f"BOOM ANGLE (ILLUSTRATIVE): {scene['boom_angle_degrees']:.0f} deg  |  RIGGING LEGS: {scene['rigging_legs']}",
        fill="#9ab6b7", font=("Segoe UI", text_size),
    )
    canvas.create_text(
        px(35), py(544), anchor="w",
        text="CONCEPTUAL ONLY / NOT TO SCALE / NOT FOR LIFT EXECUTION",
        fill="#ffca9d", font=("Segoe UI", text_size),
    )


def render_scene_html(scene):
    scene = _validate_scene(dict(scene))
    svg = render_scene_svg(scene)
    title = html.escape(scene["title"], quote=True)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
html,body{{margin:0;width:100%;height:100%;background:#07151b;color:#f2f4ed;font-family:Segoe UI,Arial,sans-serif}}
body{{display:flex;flex-direction:column;padding:12px;box-sizing:border-box}}
h1{{margin:0 0 10px;color:#66d4c0;font-size:18px}}
.drawing{{flex:1;min-height:0;display:flex;align-items:center;justify-content:center}}
svg{{width:100%;height:100%;max-height:650px}}
.notes{{color:#ffca9d;font-size:12px}}
</style></head><body><h1>AI-assisted lift scene</h1><div class="drawing">{svg}</div>
<div class="notes">Illustrative sketch only. Verify every position, dimension, rigging detail, capacity and operating condition independently.</div></body></html>'''


def save_scene_html(scene, output_path=None):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(output_path) if output_path else OUTPUT_DIR / "ai_lift_scene.html"
    path.write_text(render_scene_html(scene), encoding="utf-8")
    return path