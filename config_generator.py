import os
import re

def analyze_html(html):
    html = html.lower()

    actions = []

    # 🔹 detect input fields
    if "<input" in html:
        actions.append({"type": "input", "selector": "input"})

    # 🔹 detect password/login
    if "password" in html:
        actions.append({"type": "input", "selector": "password"})
        actions.append({"type": "click", "selector": "login"})

    # 🔹 detect buttons
    if "<button" in html:
        actions.append({"type": "click", "selector": "button"})

    # 🔹 detect file upload
    if "type=\"file\"" in html or "type='file'" in html:
        actions.append({"type": "upload_test"})  # 🔥 custom action

    # always add wait + screenshot
    actions.append({"type": "wait", "time": 2})
    actions.append({"type": "screenshot", "name": "final"})

    return actions

def generate_basic_tests(project_path):
    tests = []

    print("\n🚀 START: Basic Config Generation")

    # -------------------------
    # 🔹 1. Detect API endpoints
    # -------------------------
    api_pattern = re.compile(r'@app\.(get|post|put|delete)\("([^"]+)"')

    for root, dirs, files in os.walk(project_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                        matches = api_pattern.findall(content)

                        valid_routes = ["/", "/start-test"]
                        for method, route in matches:
                            # skip invalid/generated routes
                            if route not in valid_routes:
                                print(f"⚠️ Skipping unknown route: {route}")
                                continue
                            tests.append({
                                "name": f"{method.upper()} {route}",
                                "type": "api",
                                "category": "smoke",
                                "method": method.upper(),
                                "url": f"http://127.0.0.1:8000{route}",
                                "expected_status": 200
                            })
                except:
                    continue

    # -------------------------
    # 🔹 2. FIND BEST HTML ENTRY
    # -------------------------
    entry_html = None

    for root, dirs, files in os.walk(project_path):
        for file in files:
            if file.lower() == "index.html":
                entry_html = os.path.join(root, file)
                break
        if entry_html:
            break

    # fallback → first html
    if not entry_html:
        for root, dirs, files in os.walk(project_path):
            for file in files:
                if file.endswith(".html"):
                    entry_html = os.path.join(root, file)
                    break
            if entry_html:
                break

    # -------------------------
    # 🔹 3. CREATE UI TEST (ONLY ONE)
    # -------------------------
    if entry_html:
        abs_path = os.path.abspath(entry_html).replace("\\", "/")

        # 🔥 READ HTML CONTENT
        with open(entry_html, "r", encoding="utf-8", errors="ignore") as f:
            html_content = f.read()
            actions = analyze_html(html_content)
            
            tests.append({
                "name": "UI Functional Test",
                "type": "ui",
                "category": "functional",
                "url": f"file:///{abs_path}",
                "actions": actions,
                "assert": {
                    "type": "url_contains",
                    "value": ""
                }
            })

        print(f"🌐 UI Entry Found: {abs_path}")

    # -------------------------
    # 🔹 4. FINAL FALLBACK
    # -------------------------
    if not tests:
        tests.append({
            "name": "Default UI Test",
            "type": "ui",
            "category": "functional",
            "url": "http://127.0.0.1:8000",
            "actions": [
                {"type": "wait", "time": 2},
                {"type": "screenshot", "name": "default"}
            ],
            "assert": {
                "type": "url_contains",
                "value": ""
            }
        })

    print("✅ COMPLETED: Basic Config Generation")
    print("🧠 Generated Actions:", actions)

    return {"tests": tests}