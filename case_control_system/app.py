import json
import tempfile
from pathlib import Path
import gradio as gr

from scripts.case_control_engine import load_records, route, report


def run_case_control(input_text: str, input_type: str):
    if not input_text.strip():
        return "No input provided.", ""
    suffix_map = {"JSON": ".json", "JSONL": ".jsonl", "CSV": ".csv", "TXT/MD": ".md"}
    suffix = suffix_map.get(input_type, ".md")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"evidence{suffix}"
        path.write_text(input_text, encoding="utf-8")
        try:
            rows = [route(record) for record in load_records(path)]
            return report(rows), "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
        except Exception as exc:
            return f"Build failed: {exc}", ""


with gr.Blocks(title="Case Control System") as demo:
    gr.Markdown("# Case Control System\nPaste evidence records and generate source-status, bridge-record, discovery, deposition, and exhibit-card outputs.")
    input_type = gr.Radio(["JSON", "JSONL", "CSV", "TXT/MD"], value="JSON", label="Input type")
    input_text = gr.Textbox(lines=18, label="Evidence input")
    run_btn = gr.Button("Build case-control report")
    report_box = gr.Markdown(label="Report")
    routed_jsonl = gr.Textbox(lines=12, label="Routed JSONL")
    run_btn.click(run_case_control, inputs=[input_text, input_type], outputs=[report_box, routed_jsonl])

if __name__ == "__main__":
    demo.launch()
