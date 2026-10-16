"""Smoke-test the complete app.py control flow without a browser.

A small Streamlit API stub captures UI output so tests can run offline without
installing Streamlit. These are application-flow tests, not real-browser tests.
Run: python test_app_smoke.py
"""
from __future__ import annotations
import io
import sys
import types
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"

class StopSignal(Exception):
    pass

class Container:
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): return False

class FakeStreamlit(types.ModuleType):
    def __init__(self, dataset="Real Wikipedia revisions", strategy="ChronoRAG version-aware retrieval", question="", uploaded_file=None, show_all=False):
        super().__init__("streamlit")
        self.dataset = dataset
        self.strategy = strategy
        self.question = question
        self.uploaded_file = uploaded_file
        self.show_all_value = show_all
        self.messages: list[tuple[str, str]] = []
        self.sidebar = Container()

    def _record(self, kind: str, *args: Any, **kwargs: Any):
        val = " ".join(str(x) for x in args)
        self.messages.append((kind, val))
        return None

    def set_page_config(self, *args, **kwargs): return None
    def cache_data(self, fn=None, **kwargs):
        if fn is None:
            return lambda real_fn: real_fn
        return fn
    def title(self, *a, **k): return self._record("title", *a, **k)
    def subheader(self, *a, **k): return self._record("subheader", *a, **k)
    def header(self, *a, **k): return self._record("header", *a, **k)
    def markdown(self, *a, **k): return self._record("markdown", *a, **k)
    def write(self, *a, **k): return self._record("write", *a, **k)
    def info(self, *a, **k): return self._record("info", *a, **k)
    def warning(self, *a, **k): return self._record("warning", *a, **k)
    def success(self, *a, **k): return self._record("success", *a, **k)
    def caption(self, *a, **k): return self._record("caption", *a, **k)
    def error(self, *a, **k): return self._record("error", *a, **k)
    def dataframe(self, *a, **k): return self._record("dataframe", "dataframe")
    def expander(self, *a, **k): return Container()
    def columns(self, spec, *a, **k):
        n = spec if isinstance(spec, int) else len(spec)
        return [Container() for _ in range(n)]
    def radio(self, label, options, index=0, **kwargs):
        if label == "Choose dataset": return self.dataset
        if label == "Retrieval strategy": return self.strategy
        return options[index]
    def file_uploader(self, *a, **k): return self.uploaded_file
    def checkbox(self, *a, **k): return self.show_all_value
    def selectbox(self, label, options, **kwargs): return options[0]
    def text_input(self, label, *args, **kwargs): return self.question
    def stop(self): raise StopSignal()


def run_case(**kwargs) -> FakeStreamlit:
    fake = FakeStreamlit(**kwargs)
    previous = sys.modules.get("streamlit")
    sys.modules["streamlit"] = fake
    try:
        namespace = {"__file__": str(APP), "__name__": "__main__"}
        try:
            exec(compile(APP.read_text(encoding="utf-8"), str(APP), "exec"), namespace)
        except StopSignal:
            pass
    finally:
        if previous is None:
            sys.modules.pop("streamlit", None)
        else:
            sys.modules["streamlit"] = previous
    return fake


def output(fake: FakeStreamlit) -> str:
    return "\n".join(f"{kind}: {msg}" for kind, msg in fake.messages)


def main() -> int:
    checks: list[str] = []
    def check(cond: bool, label: str):
        if not cond:
            raise AssertionError(label)
        checks.append("PASS: " + label)

    bot_q = "What changed between versions of the COVID-19 pandemic in Africa article regarding Botswana?"
    bot = run_case(question=bot_q)
    bot_out = output(bot)
    check("Revision 946149857" in bot_out, "ChronoRAG Botswana flow selects the latest stored revision")
    check("more than 100 people" in bot_out and "more than 50 people" in bot_out, "ChronoRAG Botswana flow renders earlier and later changes")
    check("These are text differences, not automatically verified contradictions" in bot_out, "UI labels detected changes without claiming verified contradictions")

    baseline = run_case(strategy="Baseline RAG retrieval", question=bot_q)
    base_out = output(baseline)
    check("Revision 946148507" in base_out, "baseline Botswana flow selects the earlier high-similarity revision")
    check("more than 100 people" in base_out and "more than 50 people" in base_out, "baseline flow still displays the version comparison")

    alg_q = "What changed between versions of the COVID-19 pandemic in Africa article regarding Algeria?"
    alg = run_case(question=alg_q)
    alg_out = output(alg)
    check("No changes were detected in the selected comparison passages" in alg_out, "Algeria negative example shows no topic-specific difference")

    chu_q = "What changed between versions of the ChuChu TV article?"
    chu = run_case(question=chu_q)
    chu_out = output(chu)
    check("Revision 863373029" in chu_out, "ChuChu TV flow selects the latest stored revision")
    check("42nd most subscribed" in chu_out and "43rd most subscribed" in chu_out, "ChuChu TV flow renders the ranking change")

    no_match = run_case(question="zxqvbn kjhgfds qqqqwwwee")
    no_match_out = output(no_match)
    check("No lexical match was found in this collection" in no_match_out, "unmatched query shows a helpful warning")
    check("ChronoRAG result" not in no_match_out and "Baseline retrieval result" not in no_match_out, "unmatched query avoids presenting an arbitrary document as a match")

    demo_q = "How many annual leave days do full-time employees receive?"
    demo = run_case(dataset="Synthetic demo", question=demo_q)
    demo_out = output(demo)
    check("Annual Leave Policy" in demo_out and "25 paid annual leave days" in demo_out, "synthetic demo flow answers from its latest annual leave policy version")

    all_versions = run_case(question=chu_q, show_all=True)
    check("All loaded revisions" in output(all_versions), "show-all-versions option renders the loaded revision table")

    valid_upload = io.BytesIO((ROOT / "data" / "demo_documents.csv").read_bytes())
    uploaded = run_case(question=demo_q, uploaded_file=valid_upload)
    uploaded_out = output(uploaded)
    check("Loaded 12 uploaded document versions" in uploaded_out, "valid six-column CSV upload is accepted")
    check("Annual Leave Policy" in uploaded_out, "valid uploaded dataset can be searched and compared")

    bad_upload = io.BytesIO(b"title,text\nBad,content\n")
    malformed = run_case(question=demo_q, uploaded_file=bad_upload)
    malformed_out = output(malformed)
    check("Could not load documents: Missing required columns" in malformed_out, "malformed uploaded CSV displays a readable validation error")

    print("ChronoRAG App Flow Smoke Tests")
    print("==============================")
    print("Note: Streamlit API is stubbed; these test app logic/control flow, not an actual browser rendering.")
    print("\n".join(checks))
    print(f"\nTOTAL: {len(checks)} checks passed; 0 failures.")
    report_path = ROOT / "APP_FLOW_TEST_REPORT.txt"
    report_path.write_text("ChronoRAG App Flow Smoke Tests\n==============================\nNote: Streamlit API is stubbed; these test app logic/control flow, not an actual browser rendering.\n" + "\n".join(checks) + f"\n\nTOTAL: {len(checks)} checks passed; 0 failures.\n", encoding="utf-8")
    print(f"Report saved to: {report_path}")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"APP FLOW TEST FAILURE: {exc}", file=sys.stderr)
        raise
