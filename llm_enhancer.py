import os
import json
import re
from groq import Groq   # ✅ NEW

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def read_project_files(project_path, max_files=3, max_chars=3000):
    content = ""
    count = 0

    for root, dirs, files in os.walk(project_path):
        for file in files:
            if file.endswith((".py", ".html")):
                try:
                    with open(os.path.join(root, file), "r", encoding="utf-8", errors="ignore") as f:
                        file_content = f.read()

                        # 🔥 LIMIT SIZE PER FILE
                        file_content = file_content[:1000]

                        content += f"\n\n# FILE: {file}\n{file_content}"

                    count += 1
                    if count >= max_files:
                        return content[:max_chars]  # 🔥 FINAL LIMIT
                except:
                    continue

    return content[:max_chars]


def enhance_config_with_llm(config, project_path):
    try:
        print("🤖 Generating FUNCTIONAL tests using Groq...")

        project_code = read_project_files(project_path)

        # 🔥 detect index.html path
        ui_url = None
        for root, dirs, files in os.walk(project_path):
            if "index.html" in files:
                ui_url = f"file:///{os.path.join(root, 'index.html').replace('\\', '/')}"
                break
        if not ui_url:
            ui_url = "http://localhost:8000"
                
        prompt = f"""
You are a senior QA automation engineer.

Analyze the given project and generate REAL FUNCTIONAL UI TESTS.

PROJECT CODE:
{project_code}

GOAL:
Test actual functionality like a real user.

YOU MUST TEST:
1. Buttons → click and verify response
2. Forms → input + submit
3. File upload (if present)
   - valid file (docx) → should PASS
   - invalid file (pdf) → should FAIL

RULES:
- Max 3 tests only
- Use simple selectors: "button", "input"
- Include realistic steps
- Always include screenshot steps
- Use action types supported by runner:
    - click
    - input
    - wait
    - screenshot
    - upload_test  ✅ IMPORTANT

ASSERTIONS:
- url_contains OR text_present

OUTPUT STRICT JSON ONLY:

{{
  "tests": [
    {{
      "name": "Form Submission Test",
      "type": "ui",
      "category": "functional",
      "url": "{ui_url}",
      "actions": [
        {{ "type": "input", "selector": "input" }},
        {{ "type": "click", "selector": "button" }},
        {{ "type": "wait", "time": 2 }},
        {{ "type": "screenshot", "name": "after_submit" }}
      ],
      "assert": {{
        "type": "url_contains",
        "value": ""
      }}
    }},
    {{
      "name": "File Upload Validation Test",
      "type": "ui",
      "category": "functional",
      "url": "{ui_url}",
      "actions": [
        {{ "type": "upload_test" }},
        {{ "type": "wait", "time": 2 }},
        {{ "type": "screenshot", "name": "upload_result" }}
      ],
      "assert": {{
        "type": "url_contains",
        "value": ""
      }}
    }}
  ]
}}
"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        text = response.choices[0].message.content.strip()

        print("✅ LLM Response received")

        # ✅ CLEAN JSON
        text = re.sub(r"```json|```", "", text).strip()
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        text = text[json_start:json_end]

        generated = json.loads(text)

        # ✅ FILTER ONLY FUNCTIONAL UI TESTS
        filtered_tests = [
            t for t in generated.get("tests", [])
            if t.get("type") == "ui" and t.get("category") == "functional"
        ]

        # ✅ LIMIT
        filtered_tests = filtered_tests[:3]

        if not filtered_tests:
            print("⚠️ No functional tests from LLM → using base config")
            return config

        # ✅ MERGE
        # 🔥 ONLY FUNCTIONAL TESTS (PHASE 1) 
        if not filtered_tests:
            print("⚠️ No functional tests from LLM → using base config")
            return config
        
        # 🔥 MERGE instead of replace
        return {
            "tests": config["tests"] + filtered_tests
          }
        

    except Exception as e:
        print("❌ LLM ERROR:", e)
        print("⚠️ Falling back to basic config")
        return config
    
# ======================================================
# 🤖 AI FAILURE ANALYSIS (NEW - SEPARATE FEATURE)
# ======================================================

def generate_failure_analysis(test_result):
    try:

        print("🤖 Generating AI failure analysis...")

        prompt = f"""
You are a senior QA engineer.

Analyze the failed test result and provide:

1. Possible root cause
2. Possible reason
3. Suggested fix

TEST NAME:
{test_result.get("name")}

STATUS:
{test_result.get("status")}

DETAILS:
{test_result.get("details")}

STEPS:
{json.dumps(test_result.get("steps", []), indent=2)}

Keep response short and human readable.
Maximum 5 lines.
"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3
        )

        analysis = response.choices[0].message.content.strip()

        print("✅ AI analysis generated")

        return analysis

    except Exception as e:
        print("❌ AI Analysis Error:", e)

        return "AI analysis unavailable"