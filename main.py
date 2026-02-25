import sys
import os
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- SOLID IMPORTS ---
from SOLID.SRP_Detection_Final import get_srp_report
from SOLID.OCP_Detection_Final import get_ocp_report
from SOLID.Liskov_Substitution_Principle import get_lsp_report
from SOLID.ISP_detect import get_isp_report
from SOLID.dependancy_principle import get_dip_report

# --- COMPLEXITY IMPORT ---
from Complexity.Complexity_Code import estimate_complexity

# --- CLEAN CODE IMPORT ---
from Clean_code.clean_code import analyze_code_string as get_clean_report


# --- FASTAPI APP ---
app = FastAPI()


def analyze_code_payload(code_str: str):
    try:
        if not code_str.strip():
            return {
                "time_complexity": "O(1)",
                "space_complexity": "O(1)",
                "solid_report": {},
                "clean_report": {},
                "total_violations": 0
            }

        print("--- DEBUG: Starting Analysis ---")

        # 1. Complexity
        time_c, space_c = estimate_complexity(code_str)
        results = {
            "time_complexity": time_c,
            "space_complexity": space_c
        }
        print("DEBUG: Complexity Done")

        # 2. SOLID
        s_data = get_srp_report(code_str)
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
            print("DEBUG: Calling Clean Code Engine...")
            results["clean_report"] = get_clean_report(code_str)
            print("DEBUG: Clean Code Done")
        except Exception as clean_err:
            print(f"DEBUG: Clean Code Error: {clean_err}")
            results["clean_report"] = {
                "error": "Module failed",
                "naming_quality": {"naming_score": 0, "issues": []}
            }

        # 4. Stats
        results["total_violations"] = sum(
            1 for v in [s_data, o_data, l_data, i_data, d_data]
            if v.get("status") == "Violation"
        )

        print("--- DEBUG: Analysis Complete ---")
        return results

    except Exception as e:
        print(f"CRITICAL Analysis Error: {e}")
        return {
            "error": str(e),
            "solid_report": {},
            "clean_report": {},
            "total_violations": 0
        }


@app.websocket("/ws/analyze")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket Connected!")
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            code = payload.get("code", "")
            report = analyze_code_payload(code)
            await websocket.send_json(report)
            print("Response sent to Frontend!")
    except WebSocketDisconnect:
        print("WebSocket Disconnected")