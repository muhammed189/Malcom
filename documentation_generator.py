import html
import json
from pathlib import Path

from ai_diagram import render_scene_svg
from plan_schema import PLAN_SECTIONS, get_missing_required_fields

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def _display_value(value):
        if value is None or value == "":
                return "Not provided"
        if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=True)
        return str(value)


def _escape(value):
        return html.escape(_display_value(value), quote=True).replace("\n", "<br>")


def _field_value(plan_data, key):
        return _escape(plan_data.get(key))


def _summary_item(plan_data, key, label):
        return (
                '<div class="summary-item">'
                f'<span>{html.escape(label)}</span>'
                f'<strong>{_field_value(plan_data, key)}</strong>'
                "</div>"
        )


def _crane_schematic():
        return '''
        <svg class="crane-drawing" viewBox="0 0 620 510" role="img" aria-labelledby="drawing-title drawing-desc">
            <title id="drawing-title">Indicative mobile crane lift schematic</title>
            <desc id="drawing-desc">Schematic crane, boom, suspended load and deployed outrigger pads. Not to scale and not an engineered drawing.</desc>
            <defs>
                <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
                    <path d="M 32 0 L 0 0 0 32" fill="none" stroke="#123e49" stroke-width="1"/>
                </pattern>
                <linearGradient id="boom" x1="0" x2="1" y1="1" y2="0">
                    <stop offset="0" stop-color="#f5bb3d"/><stop offset="1" stop-color="#ffe17a"/>
                </linearGradient>
            </defs>
            <rect width="620" height="510" fill="url(#grid)"/>
            <path d="M28 405 H592" stroke="#85b7b2" stroke-width="3"/>
            <path d="M105 377 H414 L445 398 H83 Z" fill="#dba52e" stroke="#f5cf64" stroke-width="3"/>
            <path d="M130 333 H226 L260 377 H112 Z" fill="#e8b333" stroke="#f5cf64" stroke-width="3"/>
            <path d="M143 344 H185 V369 H122 Z" fill="#193b45" stroke="#8ab9b0" stroke-width="2"/>
            <path d="M190 344 H222 L244 369 H190 Z" fill="#193b45" stroke="#8ab9b0" stroke-width="2"/>
            <path d="M300 371 L338 371 L470 79 L438 68 Z" fill="url(#boom)" stroke="#ffdf73" stroke-width="4"/>
            <path d="M315 366 L449 83" fill="none" stroke="#fff0ae" stroke-width="3"/>
            <circle cx="312" cy="367" r="14" fill="#254851" stroke="#ffdc69" stroke-width="5"/>
            <path d="M449 74 L491 50" stroke="#ffdf73" stroke-width="9"/>
            <circle cx="491" cy="50" r="8" fill="#f5cf64"/>
            <path d="M491 58 V213" stroke="#d6e3d8" stroke-width="3"/>
            <path d="M478 213 Q491 228 504 213" fill="none" stroke="#d6e3d8" stroke-width="4"/>
            <path d="M477 218 L448 271 M505 218 L534 271" stroke="#72d6c3" stroke-width="3"/>
            <path d="M448 271 H534 L526 336 H456 Z" fill="#91a9a5" stroke="#d4e1d5" stroke-width="3"/>
            <path d="M458 287 H524 M457 311 H529" stroke="#667f7d" stroke-width="2"/>
            <path d="M104 380 V408 M408 380 V408" stroke="#72d6c3" stroke-width="7"/>
            <path d="M78 408 H132 M382 408 H436" stroke="#d2bd72" stroke-width="9"/>
            <circle cx="152" cy="393" r="27" fill="#122a32" stroke="#b9c8bd" stroke-width="5"/>
            <circle cx="152" cy="393" r="9" fill="#738c84"/>
            <circle cx="353" cy="393" r="27" fill="#122a32" stroke="#b9c8bd" stroke-width="5"/>
            <circle cx="353" cy="393" r="9" fill="#738c84"/>
            <path d="M383 364 L438 352" stroke="#72d6c3" stroke-width="2"/>
            <text x="442" y="350" fill="#8de0cf" font-size="14" font-family="Segoe UI, sans-serif">OUTRIGGER</text>
            <path d="M534 300 L577 282" stroke="#8ab9b0" stroke-width="2"/>
            <text x="500" y="270" fill="#d7e4db" font-size="14" font-family="Segoe UI, sans-serif">LOAD</text>
            <text x="40" y="472" fill="#8ab9b0" font-size="13" font-family="Segoe UI, sans-serif">SCHEMATIC ONLY  /  NOT TO SCALE</text>
        </svg>
        '''


def _build_html(plan_data, completeness, results):
        within_wll = results and results.get("capacity_check") == "Within entered WLL"
        result_class = "within" if within_wll else "exceeds"
        result_text = results.get("capacity_check", "SCREENING NOT AVAILABLE") if results else "SCREENING NOT AVAILABLE"
        ai_scene = plan_data.get("ai_scene")
        if ai_scene:
                scene_markup = render_scene_svg(ai_scene)
                scene_heading = "AI-DRAFTED LIFT SCENE / VERIFY BEFORE USE"
                scene_caption = "AI-assisted conceptual drawing. Not to scale; independently verify all geometry and rigging."
        else:
                scene_markup = _crane_schematic()
                scene_heading = "LIFT CONFIGURATION / INDICATIVE VIEW"
                scene_caption = "Illustrative only. Dimensions and equipment geometry are not modeled or to scale."

        given_items = [
                ("project_name", "PROJECT / CLIENT"),
                ("plan_reference", "PLAN REFERENCE"),
                ("planned_date", "PLANNED DATE"),
                ("load_description", "LOAD"),
                ("load_weight", "LOAD WEIGHT (t)"),
                ("load_dimensions", "LOAD SIZE (m)"),
                ("load_weight_source", "WEIGHT VERIFIED BY"),
                ("center_of_gravity", "CoG / DATUM"),
                ("crane_make_model", "CRANE"),
                ("crane_operating_weight", "CRANE MASS (t)"),
                ("working_radius", "WORKING RADIUS (m)"),
                ("gross_load", "GROSS LOAD (t)"),
                ("chart_capacity", "CHART CAPACITY (t)"),
                ("outrigger_extension", "OUTRIGGER EXT. (m)"),
                ("equipment_specs", "RIGGING SETUP"),
        ]
        given_markup = "".join(_summary_item(plan_data, key, label) for key, label in given_items)

        screening_markup = """
            <div class="formula-label">SLING LEG SCREEN</div>
            <div class="formula">T<sub>leg</sub> = W × LF / (n × sin θ)</div>
        """
        if results:
                screening_markup += (
                        f'<div class="metric"><span>Estimated leg load</span><strong>{_escape(results.get("estimated_leg_load_t"))} t</strong></div>'
                        f'<div class="metric"><span>Entered leg WLL</span><strong>{_escape(results.get("rated_capacity_per_leg_t"))} t</strong></div>'
                        f'<div class="metric"><span>WLL utilization</span><strong>{_escape(results.get("utilization_percent"))}%</strong></div>'
                        f'<div class="metric"><span>Leg angle / bearing legs</span><strong>{_escape(results.get("sling_angle_degrees"))}° / {_escape(results.get("number_of_load_bearing_legs"))}</strong></div>'
                )
        else:
                screening_markup += '<div class="metric"><span>Screening data</span><strong>Not provided</strong></div>'

        detail_sections = []
        for section_name, fields in PLAN_SECTIONS:
                rows = []
                for key, label in fields:
                        rows.append(
                                f'<tr><th scope="row">{html.escape(label)}</th>'
                                f'<td>{_field_value(plan_data, key)}</td></tr>'
                        )
                detail_sections.append(
                        f'<section class="detail-section"><h3>{html.escape(section_name)}</h3>'
                        f'<table><tbody>{"".join(rows)}</tbody></table></section>'
                )

        missing_fields = completeness.get("missing_fields", [])
        missing_markup = ""
        if missing_fields:
                missing_markup = (
                        '<div class="missing-items"><strong>BASELINE ITEMS TO COMPLETE</strong>'
                        f'<p>{" · ".join(html.escape(item) for item in missing_fields)}</p></div>'
                )

        status = _escape(completeness.get("status", "INCOMPLETE DRAFT"))
        plan_reference = _field_value(plan_data, "plan_reference")
        project_name = _field_value(plan_data, "project_name")
        result_note = _escape(results.get("status", "")) if results else "No screening result generated"
        limitations = _escape(results.get("limitations", "")) if results else ""

        return f'''<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Lift Plan | {project_name}</title>
    <style>
        :root {{ color-scheme: dark; --ink:#07151b; --panel:#0b2028; --line:#23606a; --teal:#66d4c0; --muted:#9ab6b7; --paper:#f2f4ed; --yellow:#f4c64c; --red:#ff6b62; }}
        * {{ box-sizing:border-box; }}
        body {{ margin:0; background:#d6dfdc; color:var(--paper); font:14px/1.4 "Segoe UI", Arial, sans-serif; }}
        .poster {{ width:min(100%, 1050px); margin:24px auto; padding:22px; background:var(--ink); border:1px solid var(--line); box-shadow:0 14px 38px #102a2b33; }}
        .masthead {{ display:flex; justify-content:space-between; align-items:end; gap:16px; padding:0 2px 14px; border-bottom:2px solid var(--teal); }}
        .brand {{ color:var(--teal); font-size:12px; font-weight:800; letter-spacing:2px; }}
        h1 {{ margin:3px 0 0; font-size:24px; line-height:1.1; }}
        .doc-meta {{ color:var(--muted); text-align:right; font-size:12px; }}
        .draft-warning {{ margin:12px 0; padding:8px 11px; border:1px solid #a95750; color:#ffd1c4; background:#311e22; font-weight:700; }}
        .board {{ display:grid; grid-template-columns:minmax(0, .88fr) minmax(0, 1.45fr) minmax(0, .9fr); grid-template-rows:minmax(420px, auto) auto; border-top:1px solid var(--line); border-left:1px solid var(--line); }}
        .panel {{ min-width:0; padding:13px; border-right:1px solid var(--line); border-bottom:1px solid var(--line); background:linear-gradient(145deg,#0c242b,#08171d); }}
        .panel h2 {{ margin:0 0 12px; color:var(--paper); font-family:Georgia,serif; font-size:19px; }}
        .summary-item {{ margin:0 0 7px; padding-bottom:6px; border-bottom:1px solid #173b44; }}
        .summary-item span,.metric span {{ display:block; color:var(--muted); font-size:9px; font-weight:700; letter-spacing:.8px; }}
        .summary-item strong {{ display:block; margin-top:2px; overflow-wrap:anywhere; font-size:12px; }}
        .scene {{ display:flex; min-height:420px; flex-direction:column; justify-content:space-between; background:#071a20; }}
        .scene-head {{ color:var(--teal); font-size:10px; font-weight:800; letter-spacing:1.1px; }}
        .crane-drawing {{ display:block; width:100%; max-height:380px; }}
        .scene-caption {{ color:var(--muted); font-size:10px; }}
        .formula-label {{ margin:8px 0; color:var(--yellow); font-size:10px; font-weight:800; letter-spacing:.8px; }}
        .formula {{ margin:9px 0 18px; padding:10px 6px; border:1px solid #44737a; color:#fff1b5; text-align:center; font:17px Georgia,serif; }}
        .metric {{ margin:0 0 12px; padding-bottom:8px; border-bottom:1px solid #173b44; }}
        .metric strong {{ display:block; margin-top:3px; font-size:17px; }}
        .not-evaluated {{ margin-top:14px; padding:9px; border:1px solid #a95750; color:#ffc5b8; font-size:11px; font-weight:700; }}
        .result-panel {{ grid-column:1 / -1; display:grid; grid-template-columns:1fr auto; align-items:center; gap:12px; }}
        .result-panel h2 {{ margin:0 0 5px; }}
        .result-value {{ color:var(--teal); font-size:clamp(25px, 5vw, 48px); font-weight:900; line-height:1; text-align:right; }}
        .result-value.exceeds {{ color:var(--red); }}
        .result-subtitle {{ color:var(--muted); font-size:11px; }}
        .missing-items {{ grid-column:1 / -1; margin-top:5px; padding:8px 10px; border-left:3px solid var(--yellow); background:#282719; color:#f7eab5; font-size:11px; }}
        .missing-items p {{ margin:3px 0 0; }}
        .disclaimer {{ margin:10px 0 0; color:var(--muted); font-size:10px; }}
        .appendix {{ width:min(100%, 1050px); margin:0 auto 24px; padding:22px; background:var(--ink); border:1px solid var(--line); }}
        .appendix h2 {{ margin:0 0 16px; color:var(--teal); font-size:20px; }}
        .details-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
        .detail-section {{ break-inside:avoid; border:1px solid var(--line); }}
        .detail-section h3 {{ margin:0; padding:8px 10px; color:var(--paper); background:#102d34; font-size:13px; }}
        table {{ width:100%; border-collapse:collapse; font-size:11px; }}
        th,td {{ padding:6px 8px; border-top:1px solid #173b44; text-align:left; vertical-align:top; overflow-wrap:anywhere; }}
        th {{ width:43%; color:var(--muted); font-weight:600; }}
        td {{ color:var(--paper); }}
        @media(max-width:760px) {{
            .poster,.appendix {{ margin:0; padding:12px; }}
            .board {{ grid-template-columns:1fr 1fr; grid-template-rows:auto; }}
            .scene {{ grid-column:1 / -1; grid-row:1; min-height:320px; }}
            .scene .crane-drawing {{ max-height:300px; }}
            .result-panel {{ grid-column:1 / -1; }}
            .details-grid {{ grid-template-columns:1fr; }}
            .masthead {{ align-items:start; flex-direction:column; }}
            .doc-meta {{ text-align:left; }}
        }}
        @page {{ size:A4 portrait; margin:9mm; }}
        @media print {{
            body {{ background:#fff; print-color-adjust:exact; -webkit-print-color-adjust:exact; }}
            .poster,.appendix {{ width:100%; margin:0; padding:12px; box-shadow:none; }}
            .poster {{ break-after:page; }}
            .board {{ grid-template-columns:minmax(0,.88fr) minmax(0,1.45fr) minmax(0,.9fr); grid-template-rows:175mm auto; }}
            .scene {{ grid-column:auto; grid-row:auto; min-height:175mm; }}
            .scene .crane-drawing {{ max-height:145mm; }}
            .details-grid {{ grid-template-columns:1fr 1fr; }}
            .detail-section {{ break-inside:avoid; }}
            a {{ color:inherit; text-decoration:none; }}
        }}
    </style>
</head>
<body>
    <main class="poster">
        <header class="masthead">
            <div><div class="brand">MALCOM / LIFT PLANNING</div><h1>Lift Plan Screening</h1></div>
            <div class="doc-meta"><strong>{plan_reference}</strong><br>{project_name}</div>
        </header>
        <div class="draft-warning">PRELIMINARY PLAN - COMPETENT PERSON REVIEW REQUIRED - NOT LIFT APPROVAL</div>
        <div class="board">
            <section class="panel">
                <h2>① GIVEN</h2>
                {given_markup}
            </section>
            <section class="panel scene">
                <div class="scene-head">{scene_heading}</div>
                {scene_markup}
                <div class="scene-caption">{scene_caption}</div>
            </section>
            <section class="panel">
                <h2>② SCREEN</h2>
                {screening_markup}
                <div class="not-evaluated">CRANE STABILITY, GROUND REACTION AND LOAD-CHART VALIDATION: NOT EVALUATED</div>
            </section>
            <section class="panel result-panel">
                <div>
                    <h2>③ RESULT</h2>
                    <div class="result-subtitle">{status} / {len(missing_fields)} baseline items missing</div>
                    <div class="result-subtitle">{result_note}</div>
                </div>
                <div class="result-value {result_class}">{html.escape(result_text)}</div>
                {missing_markup}
            </section>
        </div>
        <p class="disclaimer">{limitations}</p>
    </main>
    <section class="appendix">
        <h2>PLAN DATA / REVIEW RECORD</h2>
        <div class="details-grid">{"".join(detail_sections)}</div>
    </section>
</body>
</html>'''


def _build_text(plan_data, completeness, results):
        content = [
                "MALCOM LIFT PLAN INTAKE AND PRELIMINARY SCREENING",
                "For planning support only. Not lift approval or a substitute for competent-person review.",
        ]
        for section_name, fields in PLAN_SECTIONS:
                content.extend(["", section_name.upper()])
                for key, label in fields:
                        content.append(f"{label}: {_display_value(plan_data.get(key))}")

        missing_fields = completeness.get("missing_fields", [])
        content.extend([
                "",
                "INTAKE COMPLETENESS",
                f"Status: {completeness.get('status', 'INCOMPLETE DRAFT')}",
                f"Baseline required items missing: {len(missing_fields)}",
        ])
        if missing_fields:
                content.append("Complete these items or enter N/A with a reason:")
                content.extend(f"- {field}" for field in missing_fields)

        if results:
                content.extend([
                        "",
                        "SCREENING RESULTS",
                        f"Estimated load per leg: {results['estimated_leg_load_t']} t",
                        f"WLL utilization: {results['utilization_percent']}%",
                        f"Capacity check: {results['capacity_check']}",
                        f"Status: {results['status']}",
                        f"Limitations: {results['limitations']}",
                        "Crane stability, ground reaction and load-chart validation: NOT EVALUATED",
                ])
        ai_scene = plan_data.get("ai_scene")
        if ai_scene:
                content.extend([
                        "",
                        "AI-ASSISTED CONCEPTUAL SCENE",
                        f"Scene: {_display_value(ai_scene.get('title'))}",
                        f"Load: {_display_value(ai_scene.get('load_label'))} ({_display_value(ai_scene.get('load_kind'))})",
                        f"Crane position: {_display_value(ai_scene.get('crane_location'))}",
                        "See the HTML lifting plan for the embedded 2D drawing.",
                        "AI scene is conceptual only, not to scale, and not for lift execution.",
                ])
        return "\n".join(content)


def generate_plan(plan_data):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        completeness = plan_data.get("intake_completeness")
        if not completeness:
                missing_fields = get_missing_required_fields(plan_data)
                completeness = {
                        "status": "INCOMPLETE DRAFT" if missing_fields else "CORE INTAKE COMPLETE - REVIEW REQUIRED",
                        "missing_fields": missing_fields,
                }
        results = plan_data.get("calculation_results")

        html_path = OUTPUT_DIR / "lifting_plan.html"
        text_path = OUTPUT_DIR / "lifting_plan.txt"
        html_path.write_text(_build_html(plan_data, completeness, results), encoding="utf-8")
        text_path.write_text(_build_text(plan_data, completeness, results), encoding="utf-8")
        return str(html_path)
