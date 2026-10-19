from ai_diagram import request_scene, save_scene_html


def generate_diagrams(
    prompt,
    plan_data=None,
    history=None,
    endpoint="http://127.0.0.1:11434",
    model="qwen2.5:3b",
    provider="Ollama (local)",
    api_key="",
):
    scene, user_content = request_scene(
        prompt,
        plan_data or {},
        history or [],
        endpoint,
        model,
        provider,
        api_key,
    )
    return str(save_scene_html(scene)), scene, user_content
