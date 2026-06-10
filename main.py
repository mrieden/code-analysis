import sys
import os
import json
import re
import asyncio
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# ── Path setup for new folder structure ──────────────────────
ROOT_PATH        = os.path.dirname(os.path.abspath(__file__))   # repo root
AI_SERVICE_PATH  = os.path.join(ROOT_PATH, "ai_service", "app")
DATABASE_PATH    = os.path.join(ROOT_PATH, "database")

sys.path.insert(0, ROOT_PATH)
sys.path.insert(0, AI_SERVICE_PATH)    # for graph, services, agents, etc.
sys.path.insert(0, DATABASE_PATH)      # for auth.py, database.py

# ── SOLID / Complexity / Clean Code imports ───────────────────
from services import (
    get_srp_report, get_ocp_report, get_lsp_report,
    get_isp_report, get_dip_report,
    analyze_code_string as get_clean_report,
    estimate_complexity,
)

# ── Agent graph import ────────────────────────────────────────
from graph import build_graph
from graph.nodes import detect_language
from agents import translate_to_python

# ── Auth & DB imports ─────────────────────────────────────────
from auth import (
    get_current_user,
    router as auth_router,
    _github_get,
    _require_github_token,
    GITHUB_API,
)
from database import db

# ── LangChain ─────────────────────────────────────────────────
from langchain_core.messages import HumanMessage

from datetime import datetime

# ── FastAPI app ───────────────────────────────────────────────
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


# ─────────────────────────────────────────────────────────────
# STATIC ANALYSIS ENGINE
# ─────────────────────────────────────────────────────────────

def run_analysis_engine(code_str: str) -> dict:
    """Run complexity + SOLID + clean code detectors (real-time, no LLM)."""
    try:
        if not code_str.strip():
            return {
                "time_complexity": "O(1)",
                "space_complexity": "O(1)",
                "solid_report": {},
                "clean_report": {},
                "total_violations": 0
            }

        print("--- DEBUG: Starting Static Analysis ---")

        # 1. Complexity
        time_c, space_c = estimate_complexity(code_str)
        results = {"time_complexity": time_c, "space_complexity": space_c}
        print("DEBUG: Complexity Done")

        # 2. SOLID — SRP returns a list, normalise to dict
        s_data_raw = get_srp_report(code_str)
        if isinstance(s_data_raw, list):
            violations = [c for c in s_data_raw if c.get("status") == "Violation"]
            s_data = {
                "status": "Violation",
                "reason": violations[0].get("reason", ""),
                "suggestion": violations[0].get("suggestion", ""),
                "all_classes": s_data_raw,
            } if violations else {
                "status": "Pass",
                "reason": s_data_raw[0].get("reason", "No violations") if s_data_raw else "No classes.",
                "suggestion": "N/A",
                "all_classes": s_data_raw,
            }
        else:
            s_data = s_data_raw

        o_data = get_ocp_report(code_str)
        l_data = get_lsp_report(code_str)
        i_data = get_isp_report(code_str)
        d_data = get_dip_report(code_str)

        results["solid_report"] = {
            "S": s_data, "O": o_data, "L": l_data, "I": i_data, "D": d_data
        }
        print("DEBUG: SOLID Done")

        # 3. Clean Code
        try:
            results["clean_report"] = get_clean_report(code_str, verbose=True)
            print("DEBUG: Clean Code Done")
        except Exception as e:
            print(f"DEBUG: Clean Code Error: {e}")
            results["clean_report"] = {
                "naming_quality": {"naming_score": 0, "issues": []},
                "radon": {"maintainability_index": 0, "raw_metrics": {}},
                "pylint": []
            }

        # 4. Total violations
        results["total_violations"] = sum(
            1 for v in [s_data, o_data, l_data, i_data, d_data]
            if isinstance(v, dict) and v.get("status") == "Violation"
        )

        print("--- DEBUG: Static Analysis Complete ---")
        return results

    except Exception as e:
        print(f"CRITICAL Analysis Error: {e}")
        import traceback; traceback.print_exc()
        return {"error": str(e), "solid_report": {}, "clean_report": {}, "total_violations": 0}


# ─────────────────────────────────────────────────────────────
# AGENT PIPELINE
# ─────────────────────────────────────────────────────────────

def build_analysis_report_text(analysis: dict, code_str: str) -> str:
    """Convert static analysis dict into readable text for the Refactor Agent."""
    lines = ["=== CODE ANALYSIS REPORT ===\n"]
    lines.append(f"Time Complexity: {analysis.get('time_complexity', 'N/A')}")
    lines.append(f"Space Complexity: {analysis.get('space_complexity', 'N/A')}\n")

    lines.append("--- SOLID Principles ---")
    solid = analysis.get("solid_report", {})
    for key, name in {"S": "Single Responsibility", "O": "Open/Closed",
                      "L": "Liskov Substitution", "I": "Interface Segregation",
                      "D": "Dependency Inversion"}.items():
        r = solid.get(key, {})
        lines.append(f"{key} - {name}: {r.get('status', 'N/A')}")
        if r.get("reason") and r.get("reason") != "N/A":
            lines.append(f"   Reason: {r['reason']}")
        if r.get("suggestion") and r.get("suggestion") != "N/A":
            lines.append(f"   Suggestion: {r['suggestion']}")

    lines.append(f"\nTotal SOLID Violations: {analysis.get('total_violations', 0)}\n")

    clean = analysis.get("clean_report", {})
    naming = clean.get("naming_quality", {})
    radon  = clean.get("radon", {})
    pylint = clean.get("pylint", [])

    lines.append("--- Clean Code ---")
    lines.append(f"Naming Score: {naming.get('naming_score', 'N/A')}/100")
    mi = radon.get("maintainability_index")
    if mi is not None:
        lines.append(f"Maintainability Index: {round(mi, 2)}")
    if pylint:
        lines.append(f"Pylint Issues: {len(pylint)}")

    lines.append("\n=== ORIGINAL CODE ===")
    lines.append(code_str)
    return "\n".join(lines)


# ──────────────────────────────────────────
# SOLID-ON-DEMAND (Alt+Enter): the SOLID cards come from the Architect
# agent's *opinion* (LLM), not the deterministic detectors. Clean Code +
# Complexity stay on the live static engine. This is why the cards can now
# legitimately "have an opinion" instead of echoing the tools.
# ──────────────────────────────────────────
_ARCH_PRINCIPLE_KEY = {"SRP": "S", "OCP": "O", "LSP": "L", "ISP": "I", "DIP": "D"}


def _attr(o, k, default=None):
    """Read a field whether `o` is a Pydantic model or a model_dump() dict."""
    if isinstance(o, dict):
        return o.get(k, default)
    return getattr(o, k, default)


def _architect_to_solid_report(report) -> dict:
    """Map the Architect's solid_violations -> the {S,O,L,I,D} card shape the
    frontend SOLID report consumes. Accepts either an ArchitectReport object
    or its model_dump() dict."""
    solid = {
        k: {"status": "Pass",
            "reason": "No violation flagged by the architect.",
            "violations": []}
        for k in ("S", "O", "L", "I", "D")
    }
    for v in (_attr(report, "solid_violations", None) or []):
        key = _ARCH_PRINCIPLE_KEY.get(_attr(v, "principle", None))
        if not key:
            continue
        card = solid[key]
        if card["status"] != "Violation":
            card["status"] = "Violation"
            card["reason"] = _attr(v, "reasoning")
        card["violations"].append({
            "line": None,
            "message": _attr(v, "reasoning"),
            "detail": _attr(v, "refactor_directive"),
            "severity": _attr(v, "severity"),
            "confidence": _attr(v, "confidence"),
        })
    total = sum(1 for k in solid if solid[k]["status"] == "Violation")
    return {"solid_report": solid, "total_violations": total}


def run_solid_analysis(code_str: str) -> dict:
    """Alt+Enter handler: ask the Architect LLM for its SOLID opinion and return
    ONLY the SOLID-related fields, to be merged into the live result on the
    frontend. Complexity + Clean Code are left untouched here.

    For Java/C++ we translate to Python first (same as the live typing path),
    since the Architect reasons over the Python form."""
    try:
        if not code_str.strip():
            return {"solid_report": {}, "total_violations": 0,
                    "architect_verdict": None, "solid_source": "architect"}
        from agents.architect import _run_architect, _flatten_directives

        static = run_analysis_engine(code_str)
        analyzer_text = build_analysis_report_text(static, code_str)
        report = _run_architect(
            code=code_str,
            analyzer_report=analyzer_text,
            previously_rejected=[],
        )
        payload = _architect_to_solid_report(report)
        payload["architect_verdict"] = report.global_verdict
        payload["solid_source"] = "architect"
        # Seed for the Optimize pipeline: lets it REUSE this exact opinion
        # (verdict + directives) instead of re-asking the Architect. The handler
        # caches it against the code it ran on and strips it before sending.
        payload["_seed"] = {
            "architect_report": report.model_dump(),
            "refactor_directives": _flatten_directives(report),
            "architect_verdict": report.global_verdict,
        }
        return payload
    except Exception as e:
        print(f"DEBUG: SOLID architect analysis failed: {e}")
        import traceback; traceback.print_exc()
        return {"solid_error": str(e), "solid_source": "architect"}


def _global_score(analysis: dict) -> int:
    """Backend mirror of the frontend calculateGlobalScore (Results.tsx).

    Kept byte-for-byte in sync with the UI formula so the score ratchet below
    compares the SAME number the user sees in the Optimize before/after panel.
    Higher = better. Clean code 40 + SOLID 35 + time 15 + space 10, capped 100.
    """
    if not analysis or analysis.get("error"):
        return 0
    clean       = analysis.get("clean_report") or {}
    clean_score = clean.get("score") or 0
    clean_pts   = int((clean_score / 100.0) * 40 + 0.5)   # JS Math.round
    solid       = analysis.get("solid_report") or {}
    solid_score = sum(7 for k in ("S", "O", "L", "I", "D")
                      if (solid.get(k) or {}).get("status") == "Pass")
    time_value  = analysis.get("time_complexity") or "O(1)"
    time_score  = 15 if time_value in ("O(1)", "O(n)") else 7
    space_score = 10 if analysis.get("space_complexity") == "O(1)" else 7
    return min(100, clean_pts + solid_score + time_score + space_score)


def run_agent_pipeline(analysis: dict, code_str: str, model_key: str = "llama-3.1-8b", solid_seed: dict | None = None) -> dict:
    """
    Run the full AI agent pipeline using the new architecture:
    analyzer (direct tool call) → Refactor Agent (LLM) →
    syntax_check → Convergence (deterministic, no LLM) → executer → regression_check
    """
    try:
        print("--- DEBUG: Starting Agent Pipeline ---")

        # Build graph — new architecture takes no LLM args
        # (analyzer and executer are direct tool calls, not LLM agents)
        agent_app = build_graph()

        # The analyzer node reads from original_code directly
        # We also pass the static analysis as context in messages
        report_text = build_analysis_report_text(analysis, code_str)

        inputs = {
            "messages": [HumanMessage(content=report_text)],
            "original_code": code_str,
            "refactor_iterations": 0,
            "syntax_iterations": 0,
            "analyzer_report": "",
            "original_analyzer_report": "",
            "refactored_code": [],          # now a list[str]: full history of refactors
            "execution_result": "",
            "refactor_syntax_error": None,
            # ── deterministic-convergence pipeline fields ──
            "quality_scores": [],
            "improvement_loops": 0,
            "test_inputs": None,            # None => Characterizer will generate test cases
            "test_mode": "stdio",
            "test_driver": "",
            "regression_verdict": None,
            "regression_report": "",
        }

        # Honor a captured Alt+Enter SOLID opinion (when present for THIS code):
        # pre-seed the Architect's verdict + directives so the graph reuses them
        # on the first pass instead of re-running the Architect. The gate in
        # graph/routers.py skips the Architect node when these are present.
        if solid_seed:
            inputs["architect_report"]          = solid_seed.get("architect_report")
            inputs["refactor_directives"]       = solid_seed.get("refactor_directives")
            inputs["architect_verdict"]         = solid_seed.get("architect_verdict")
            inputs["architect_baseline_report"] = solid_seed.get("architect_report")

        final_state = None
        last_python_refactor = ""   # latest Python refactor BEFORE any translate-back
        for state in agent_app.stream(inputs, stream_mode="values"):
            final_state = state
            _rc = state.get("refactored_code")
            if isinstance(_rc, list) and _rc:
                last_python_refactor = _rc[-1]
            print(
                f"DEBUG: analyzer={bool(state.get('analyzer_report'))} | "
                f"refactors={len(state.get('refactored_code') or [])} | "
                f"scores={state.get('quality_scores')} | "
                f"regression={state.get('regression_verdict')} | "
                f"execution={bool(state.get('execution_result'))}"
            )

        if not final_state:
            return {
                "agent_report": "Agent pipeline produced no output.",
                "validator_verdict": "FAIL",
                "refactored_code": code_str,
                "suggestions": [],
                "comparator_report": "",
                "regression_verdict": "INCONCLUSIVE",
                "regression_report": "",
                "execution_result": "",
            }

        agent_report       = final_state.get("analyzer_report", "")
        execution_result   = final_state.get("execution_result", "")
        regression_verdict = final_state.get("regression_verdict") or "INCONCLUSIVE"
        regression_report  = final_state.get("regression_report", "")
        quality_scores     = final_state.get("quality_scores", [])

        # refactored_code shape depends on the path taken through the graph:
        #   - Python path keeps it a list[str] (full history of refactor attempts)
        #   - the Java/C++ translate-out node overwrites it with a single string
        #     (the final source translated back from Python)
        # Normalise both into one "latest refactor" string. Falling back to the
        # original code when nothing was produced.
        raw_refactored = final_state.get("refactored_code")
        if isinstance(raw_refactored, list):
            had_refactor    = len(raw_refactored) > 0
            refactored_code = raw_refactored[-1] if had_refactor else code_str
        elif isinstance(raw_refactored, str):
            had_refactor    = bool(raw_refactored.strip())
            refactored_code = raw_refactored if had_refactor else code_str
        else:
            had_refactor    = False
            refactored_code = code_str

        # Build a human-readable summary; kept under comparator_report for UI compat
        if quality_scores:
            comparator_report = (
                f"Quality score: {quality_scores[0]} -> {quality_scores[-1]} "
                f"across {len(quality_scores)} pass(es). "
                f"Behavior: {regression_verdict}. {regression_report}"
            )
        else:
            comparator_report = regression_report

        # Determine verdict: behavior preserved AND the code actually changed
        code_changed = had_refactor and refactored_code.strip() != code_str.strip()
        behavior_ok  = regression_verdict in ("SAME", "INCONCLUSIVE")

        if "FAIL" in execution_result.upper() and "docker" not in execution_result.lower():
            verdict = "FAIL"
        elif regression_verdict == "DIFFERENT":
            verdict = "FAIL"
        elif code_changed and behavior_ok:
            verdict = "PASS"
        elif not code_changed:
            verdict = "PASS"   # nothing needed changing — code was already clean
        else:
            verdict = "FAIL"

        # Extract suggestions from agent report
        suggestions = []
        for line in agent_report.split("\n"):
            s = line.strip()
            if s.startswith(("- ", "* ", "• ")):
                suggestions.append(s[2:].strip())
        if not suggestions:
            suggestions = ["Code has been refactored based on analysis."]

        print(f"--- DEBUG: Agent Pipeline Complete. Verdict: {verdict} ---")

        return {
            "agent_report": agent_report,
            "comparator_report": comparator_report,   # convergence/behavior summary (UI compat)
            "regression_verdict": regression_verdict,
            "regression_report": regression_report,
            "quality_scores": quality_scores,
            "execution_result": execution_result,
            "validator_verdict": verdict,
            "refactored_code": refactored_code,
            "refactored_python": last_python_refactor,   # Python form, used for re-scoring
            "suggestions": suggestions,
            "original_code_converted": final_state.get("original_code_converted", ""),
            "source_language": final_state.get("source_language", ""),
            "architect_verdict": final_state.get("architect_verdict"),
            "architect_report":  final_state.get("architect_report"),
            "architect_baseline_report": final_state.get("architect_baseline_report"),
        }

    except Exception as e:
        print(f"CRITICAL Agent Pipeline Error: {e}")
        import traceback; traceback.print_exc()
        return {
            "agent_report": f"Error: {str(e)}",
            "validator_verdict": "FAIL",
            "refactored_code": code_str,
            "suggestions": [],
            "comparator_report": "",
            "execution_result": "",
        }


# ─────────────────────────────────────────────────────────────
# HISTORY ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.get("/history")
async def get_history(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["github_id"])
    entries = await db.history.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return entries


@app.delete("/history/{entry_id}")
async def delete_history_entry(entry_id: str, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["github_id"])
    result  = await db.history.delete_one({"entry_id": entry_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"message": "Deleted successfully"}


# Multi-language repo scanning.
# Python is fully analysed in the scan; C++/Java are detected + listed, then
# deep-analysed on demand through the editor pipeline
# (detect_language -> Translate to Python -> analyzer -> ... -> Translate back).
LANG_EXTENSIONS = {
    "python": (".py", ".pyw"),
    "cpp":    (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".h", ".c"),
    "java":   (".java",),
}


def _detect_repo_language(path: str):
    lower = path.lower()
    for lang, exts in LANG_EXTENSIONS.items():
        if lower.endswith(exts):
            return lang
    return None


@app.post("/github/analyze-repo")
async def analyze_repo(payload: dict, current_user: dict = Depends(get_current_user)):
    """Scan a GitHub repo across Python / C++ / Java.

    Python files get full static analysis (SOLID + complexity + clean code).
    C++ / Java files are detected and listed; opening one in the editor and
    clicking Optimize runs the multi-language translate->analyze pipeline.
    File downloads + analysis run concurrently (bounded) with per-file timeouts
    so large repositories don't hang or trigger a NetworkError in the browser.
    """
    import base64

    token  = _require_github_token(current_user)
    owner  = payload.get("owner")
    repo   = payload.get("repo")
    branch = payload.get("branch")

    if not owner or not repo:
        raise HTTPException(status_code=400, detail="owner and repo are required")

    if not branch:
        repo_info = await _github_get(token, f"{GITHUB_API}/repos/{owner}/{repo}")
        branch = repo_info.get("default_branch", "main")

    tree = await _github_get(
        token,
        f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}",
        params={"recursive": "1"},
    )

    # Collect every supported code file together with its language.
    code_files = []
    for t in tree.get("tree", []):
        if t.get("type") != "blob":
            continue
        lang = _detect_repo_language(t.get("path", ""))
        if lang:
            code_files.append({"path": t["path"], "language": lang})

    # Scan the ENTIRE repository — no file-count cap. Large repos just take
    # longer to finish; nothing is skipped.
    truncated = False

    language_counts = {}
    for f in code_files:
        language_counts[f["language"]] = language_counts.get(f["language"], 0) + 1

    sem  = asyncio.Semaphore(6)        # cap concurrent GitHub calls
    loop = asyncio.get_event_loop()

    async def process(entry: dict) -> dict:
        path = entry["path"]
        lang = entry["language"]
        async with sem:
            try:
                # No per-file download timeout — every file is fetched in full,
                # however large or slow it is.
                data = await _github_get(
                    token,
                    f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
                    params={"ref": branch},
                )
                if not (isinstance(data, dict) and data.get("encoding") == "base64"):
                    return {"path": path, "language": lang,
                            "supported": lang == "python", "error": "unsupported encoding"}

                content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
                loc = content.count("\n") + 1

                # C++/Java: list only. Deep analysis happens in the editor flow.
                if lang != "python":
                    return {"path": path, "language": lang, "supported": False, "loc": loc}

                # Python: run the (blocking) static engine off the event loop.
                # No analysis timeout — let the static engine finish regardless
                # of how big the file is.
                analysis = await loop.run_in_executor(None, run_analysis_engine, content)
                return {"path": path, "language": lang, "supported": True,
                        "loc": loc, "analysis": analysis}

            except asyncio.TimeoutError:
                return {"path": path, "language": lang,
                        "supported": lang == "python", "error": "timed out"}
            except Exception as e:
                return {"path": path, "language": lang,
                        "supported": lang == "python", "error": str(e)}

    files = await asyncio.gather(*[process(f) for f in code_files])

    return {
        "owner": owner,
        "repo": repo,
        "branch": branch,
        "total_files": len(code_files),
        "language_counts": language_counts,
        "truncated": truncated,
        "files": files,
    }


# ─────────────────────────────────────────────────────────────
# WEBSOCKET
# ─────────────────────────────────────────────────────────────

@app.websocket("/ws/analyze")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket Connected!")

    # Run the blocking analysis/agent pipeline OFF the event loop so the
    # websocket can keep answering pings during the 30-60s optimize. If we
    # block the loop, uvicorn drops the connection and the result is lost
    # even though the pipeline finished successfully.
    loop = asyncio.get_event_loop()

    # Optional auth via token query param
    token = websocket.query_params.get("token")
    current_user = None
    if token:
        try:
            from auth import decode_token
            current_user = await decode_token(token)
        except Exception:
            pass

    # Per-connection cache of the latest Alt+Enter SOLID opinion, keyed by the
    # exact code it ran on. Optimize reuses it only when the code still matches.
    last_solid = None
    try:
        while True:
            data     = await websocket.receive_text()
            payload  = json.loads(data)
            code     = payload.get("code", "")
            trigger  = payload.get("trigger", "typing")
            model_key = payload.get("model", "llama-3.1-8b")

            # Detect language (regex heuristic, no LLM) so we never run the
            # Python-only static analyzers on Java/C++ source directly.
            lang = (detect_language({"original_code": code}) or {}).get(
                "source_language", "unknown"
            )

            if trigger == "analyze":
                # ===== Optimize click: full agent pipeline =====
                # Reuse the Alt+Enter SOLID opinion only if it was captured for
                # THIS exact code; else refactor normally (Architect runs).
                # Reuse the Alt+Enter SOLID opinion when it was captured for THIS
                # code. Match on NORMALIZED source (line endings + surrounding
                # whitespace) so a stray trailing newline / CRLF difference between
                # the 'solid' and 'analyze' messages can't silently drop the seed
                # and force a SECOND, independent Architect run that disagrees with
                # the one the user already saw on the front.
                _norm_code = code.replace("\r\n", "\n").strip()
                solid_seed = (
                    last_solid["seed"]
                    if (last_solid and (last_solid.get("code") or "").replace("\r\n", "\n").strip() == _norm_code)
                    else None
                )
                if lang in ("java", "cpp"):
                    # The graph translates source -> Python, analyzes,
                    # refactors, then translates back. Static metrics are
                    # computed on the Python translation, since Java/C++
                    # cannot be parsed by Python's ast module.
                    agent_result = await loop.run_in_executor(
                        None, run_agent_pipeline, {}, code, model_key, solid_seed
                    )
                    converted    = agent_result.get("original_code_converted") or ""
                    if converted.strip():
                        analysis_result = await loop.run_in_executor(
                            None, run_analysis_engine, converted
                        )
                        analysis_result["analyzed_code"] = converted
                    else:
                        analysis_result = {
                            "time_complexity": "N/A",
                            "space_complexity": "N/A",
                            "solid_report": {},
                            "clean_report": {},
                            "total_violations": 0,
                        }
                else:
                    analysis_result = await loop.run_in_executor(
                        None, run_analysis_engine, code
                    )
                    agent_result    = await loop.run_in_executor(
                        None, run_agent_pipeline, analysis_result, code, model_key, solid_seed
                    )

                final_response = {**analysis_result, **agent_result, "language": lang}

                # ── SOLID = the Architect's opinion, on a SINGLE consistent basis ──
                # No static SOLID anywhere. The BEFORE card/score uses the
                # Architect's view of the ORIGINAL code (the SAME opinion shown
                # live / on Alt+Enter), and the AFTER card/score uses the
                # Architect's view of the REFACTORED code. Both sides are judged
                # by the SAME evaluator, so BEFORE and AFTER always agree and an
                # unchanged refactor can never produce a phantom delta. Clean
                # Code + Complexity stay on the static engine, by design.
                #
                # BEFORE basis: reuse the seeded Alt+Enter opinion when present
                # (so Optimize "before" == exactly what the front already showed);
                # otherwise the pipeline's own first-pass (baseline) report.
                baseline_arch = (solid_seed or {}).get("architect_report") \
                    or agent_result.get("architect_baseline_report")
                final_arch = agent_result.get("architect_report")

                if baseline_arch:
                    before_card = _architect_to_solid_report(baseline_arch)
                    final_response["solid_report"]     = before_card["solid_report"]
                    final_response["total_violations"] = before_card["total_violations"]

                # Real "after" score: re-run the STATIC engine on the refactored
                # *Python* for Clean Code + Complexity only, then overwrite its
                # SOLID card with the Architect's view of that refactored code,
                # so AFTER sits on the EXACT same SOLID basis as BEFORE. If it's
                # absent or unparseable -> None, and the UI falls back to before.
                refactored_py = agent_result.get("refactored_python", "") or ""
                after_analysis = None
                if refactored_py.strip():
                    candidate = await loop.run_in_executor(
                        None, run_analysis_engine, refactored_py
                    )
                    if not candidate.get("error"):
                        after_analysis = candidate
                        if final_arch:
                            after_card = _architect_to_solid_report(final_arch)
                            after_analysis["solid_report"]     = after_card["solid_report"]
                            after_analysis["total_violations"] = after_card["total_violations"]
                final_response["refactored_analysis"] = after_analysis

                # ── Decision: driven ONLY by the Alt+Enter (BEFORE) violations ──
                # HARD RULE (no exceptions): if the Architect flagged ANY SOLID
                # violation, we ALWAYS present a refactor — never halt, never
                # silently revert to the original, never "couldn't safely improve".
                # HALT_PERFECT_ENOUGH is reserved STRICTLY for code that is already
                # clean (zero violations after Alt+Enter).
                before_viol = final_response.get("total_violations", 0)
                if before_viol > 0:
                    # Violations exist -> a refactor is mandatory. Keep the
                    # pipeline's refactored code + after-analysis exactly as
                    # produced; do NOT discard on score. Fixing SOLID issues on a
                    # consistent basis raises the rating, and the user wants the
                    # refactor shown regardless.
                    final_response["architect_verdict"] = "PROCEED_TO_REFACTOR"
                    if not (final_response.get("refactored_code") or "").strip():
                        # Safety net only: pipeline returned nothing usable.
                        final_response["refactored_code"] = refactored_py or code
                else:
                    # Zero violations -> already clean. Halt and mirror the
                    # original so BEFORE == AFTER and the score delta is exactly 0.
                    final_response["architect_verdict"]   = "HALT_PERFECT_ENOUGH"
                    final_response["refactored_code"]     = code
                    final_response["refactored_analysis"] = None

                # Save to history if user logged in
                if current_user:
                    await db.history.insert_one({
                        "entry_id":       str(datetime.utcnow().timestamp()),
                        "user_id":        str(current_user["github_id"]),
                        "created_at":     datetime.utcnow(),
                        "language":       lang,
                        "original_code":  code,
                        "analysis_report": analysis_result,
                        "refactored_code": final_response.get("refactored_code", ""),
                        "suggestions":    agent_result.get("suggestions", []),
                        "verdict":        final_response.get("validator_verdict", "FAIL"),
                    })
            elif trigger == "solid":
                # ===== Alt+Enter: SOLID opinion from the Architect (LLM) =====
                # One LLM call -> run OFF the event loop so the socket keeps
                # answering pings and the result is actually delivered.
                if lang in ("java", "cpp"):
                    try:
                        converted = (await loop.run_in_executor(
                            None, translate_to_python,
                            {"source_language": lang, "original_code": code}
                        ) or {}).get("original_code_converted", "")
                    except Exception as e:
                        print(f"DEBUG: solid translate failed: {e}")
                        converted = ""
                    target = converted if converted.strip() else code
                else:
                    target = code
                final_response = await loop.run_in_executor(
                    None, run_solid_analysis, target
                )
                final_response["language"] = lang
                # Cache this opinion against the ORIGINAL code so a following
                # Optimize on the same code can reuse it. Strip the internal
                # seed before sending to the frontend.
                _seed = final_response.pop("_seed", None)
                last_solid = {"code": code, "seed": _seed} if _seed else None
            else:
                # ===== Real-time typing: no LLM calls =====
                if lang in ("java", "cpp"):
                    # Live analysis for non-Python: translate to Python (one LLM
                    # call), then run the SAME static analyzers Python uses so
                    # the report cards populate live, just like Python. The
                    # heavy refactor pipeline still only runs on Optimize.
                    try:
                        converted = (translate_to_python(
                            {"source_language": lang, "original_code": code}
                        ) or {}).get("original_code_converted", "")
                    except Exception as e:
                        print(f"DEBUG: live translate failed: {e}")
                        converted = ""
                    if converted.strip():
                        final_response = run_analysis_engine(converted)
                        final_response["analyzed_code"] = converted
                        final_response["language"] = lang
                    else:
                        final_response = {
                            "language": lang,
                            "notice": f"Could not translate {lang.upper()} for analysis - try Optimize.",
                            "time_complexity": "N/A",
                            "space_complexity": "N/A",
                            "solid_report": {},
                            "clean_report": {},
                            "total_violations": 0,
                        }
                elif lang == "unsupported":
                    final_response = {
                        "language": "unsupported",
                        "notice": "Language not supported yet. Supported: Python, Java, C++.",
                        "time_complexity": "-",
                        "space_complexity": "-",
                        "solid_report": {},
                        "clean_report": {},
                        "total_violations": 0,
                    }
                else:
                    final_response = run_analysis_engine(code)
                    final_response["language"] = lang

            # Live typing never owns SOLID — that's the Architect's job on
            # Alt+Enter. Strip the tool SOLID so the frontend merge keeps the
            # architect's opinion intact instead of overwriting it every keystroke.
            if trigger not in ("analyze", "solid"):
                final_response.pop("solid_report", None)
                final_response.pop("total_violations", None)
            await websocket.send_json(final_response)
            print("Response sent to Frontend!")

    except WebSocketDisconnect:
        print("WebSocket Disconnected")
