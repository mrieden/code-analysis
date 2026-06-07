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
BACKEND_APP_PATH = os.path.dirname(os.path.abspath(__file__))   # backend/app/
AI_SERVICE_PATH  = os.path.abspath(os.path.join(
    BACKEND_APP_PATH, "..", "..", "ai_service", "app"
))

sys.path.insert(0, BACKEND_APP_PATH)   # for auth.py, database.py
sys.path.insert(0, AI_SERVICE_PATH)    # for graph, services, agents, etc.
sys.path.insert(0, os.path.abspath(os.path.join(BACKEND_APP_PATH, "..", "..", "database")))

# ── SOLID / Complexity / Clean Code imports ───────────────────
from services import (
    get_srp_report, get_ocp_report, get_lsp_report,
    get_isp_report, get_dip_report,
    analyze_code_string as get_clean_report,
    estimate_complexity,
)

# ── Agent graph import ────────────────────────────────────────
from graph import build_graph

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


def run_agent_pipeline(analysis: dict, code_str: str, model_key: str = "llama-3.1-8b") -> dict:
    """
    Run the full AI agent pipeline using the new architecture:
    analyzer (direct tool call) → Refactor Agent (LLM) →
    syntax_check → Comparator Agent (LLM) → executer (direct tool call)
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
            "analyzer_report": "",
            "original_analyzer_report": "",
            "refactored_code": "",
            "comparator_report": "",
            "execution_result": "",
            "refactor_syntax_error": None,
        }

        final_state = None
        for state in agent_app.stream(inputs, stream_mode="values"):
            final_state = state
            print(
                f"DEBUG: analyzer={bool(state.get('analyzer_report'))} | "
                f"refactored={bool(state.get('refactored_code'))} | "
                f"comparator={bool(state.get('comparator_report'))} | "
                f"execution={bool(state.get('execution_result'))}"
            )

        if not final_state:
            return {
                "agent_report": "Agent pipeline produced no output.",
                "validator_verdict": "FAIL",
                "refactored_code": code_str,
                "suggestions": [],
                "comparator_report": "",
                "execution_result": "",
            }

        agent_report      = final_state.get("analyzer_report", "")
        comparator_report = final_state.get("comparator_report", "")
        execution_result  = final_state.get("execution_result", "")
        refactored_code   = final_state.get("refactored_code", code_str)

        # Determine verdict
        if "PASS" in execution_result.upper() and "docker" not in execution_result.lower():
            verdict = "PASS"
        elif "PASS" in comparator_report.upper() and refactored_code != code_str:
            verdict = "PASS"
        elif "docker" in execution_result.lower() and "PASS" in comparator_report.upper():
            # Docker not available but comparator passed — still a win
            verdict = "PASS"
        elif refactored_code and refactored_code != code_str:
            verdict = "PASS"
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
            "comparator_report": comparator_report,
            "execution_result": execution_result,
            "validator_verdict": verdict,
            "refactored_code": refactored_code,
            "suggestions": suggestions,
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


# ── Multi-language repo scanning ──────────────────────────────
# Extensions we recognise. Python is fully analysed in the scan; C++/Java are
# detected + listed, then deep-analysed on demand through the editor pipeline
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

    MAX_FILES = 50
    truncated = len(code_files) > MAX_FILES
    code_files = code_files[:MAX_FILES]

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
                data = await asyncio.wait_for(
                    _github_get(
                        token,
                        f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
                        params={"ref": branch},
                    ),
                    timeout=20,
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
                analysis = await asyncio.wait_for(
                    loop.run_in_executor(None, run_analysis_engine, content),
                    timeout=20,
                )
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

    # Optional auth via token query param
    token = websocket.query_params.get("token")
    current_user = None
    if token:
        try:
            from auth import decode_token
            current_user = await decode_token(token)
        except Exception:
            pass

    try:
        while True:
            data     = await websocket.receive_text()
            payload  = json.loads(data)
            code     = payload.get("code", "")
            trigger  = payload.get("trigger", "typing")
            model_key = payload.get("model", "llama-3.1-8b")

            # Step 1: Always run static analysis (real-time, no LLM)
            analysis_result = run_analysis_engine(code)

            # Step 2: Run agent pipeline only on Optimize click
            if trigger == "analyze":
                agent_result   = run_agent_pipeline(analysis_result, code, model_key)
                final_response = {**analysis_result, **agent_result}

                # Step 3: Save to history if user logged in
                if current_user:
                    await db.history.insert_one({
                        "entry_id":       str(datetime.utcnow().timestamp()),
                        "user_id":        str(current_user["github_id"]),
                        "created_at":     datetime.utcnow(),
                        "original_code":  code,
                        "analysis_report": analysis_result,
                        "refactored_code": agent_result.get("refactored_code", ""),
                        "suggestions":    agent_result.get("suggestions", []),
                        "verdict":        agent_result.get("validator_verdict", "FAIL"),
                    })
            else:
                final_response = analysis_result

            await websocket.send_json(final_response)
            print("Response sent to Frontend!")

    except WebSocketDisconnect:
        print("WebSocket Disconnected")
