import requests
import os
import copy
import time
from PIL import Image, ImageDraw
import threading
from services.ui_runner import run_ui_test
from services.llm_enhancer import generate_failure_analysis

TEST_TIMEOUT = 300  # ⏱️ 5 mins per test


def create_api_screenshot(test_name, text, screenshot_folder):
    file_path = os.path.join(screenshot_folder, f"{test_name}.png")

    img = Image.new('RGB', (800, 400), color='white')
    d = ImageDraw.Draw(img)

    d.text((10, 10), text, fill=(0, 0, 0))

    img.save(file_path)
    return file_path
def run_ui_with_timeout(test, screenshot_folder, timeout=300):
    result_container = {}

    def target():
        result_container["result"] = run_ui_test(test, screenshot_folder)

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        print("⏰ UI Test exceeded limit → killing test")

        return {
            "name": test["name"],
            "type": test.get("category", "ui"),
            "status": "FAIL",
            "details": "UI test timeout (killed)",
            "screenshots": [],
            "steps": [
            {
                "type": "timeout",
                "name": "UI Timeout",
                "status": "FAIL",
                "message": "UI test exceeded timeout",
                "screenshot": ""
            }
        ]
    }

    return result_container.get("result", {
        "name": test["name"],
        "type": test.get("category", "ui"),
        "status": "FAIL",
        "details": "No result returned",
        "screenshots": [],
        "steps": [
            {
                "type": "system",
                "name": "Runner Error",
                "status": "FAIL",
                "message": "No result returned from UI runner",
                "screenshot": ""
            }
        ]
    })
def run_tests(config, screenshot_folder):
    results = []

    print("\n==============================")
    print("🧪 TEST EXECUTION STARTED")
    print("==============================")

    for index, test in enumerate(config["tests"]):
        test = copy.deepcopy(test)

        start_time = time.time()

        print(f"\n▶️ Running Test {index+1}: {test['name']}")
        print(f"🔹 Type: {test['type']}")

        result = {
            "name": test["name"],
            "type": test.get("category", "functional"),
            "status": "FAIL",
            "details": "",
            "screenshots": [],   # ✅ FIXED
            "steps": []          # ✅ ADD THIS (for Excel step-level report)
        }

        try:
            # ⏱️ TIMEOUT CHECK (before execution)
            if time.time() - start_time > TEST_TIMEOUT:
                print("⏰ Skipping test (timeout before start)")
                result["details"] = "Skipped due to timeout"
                results.append(result)
                continue

            # =========================
            # 🔹 API TEST
            # =========================
            if test["type"] == "api":

                print(f"🌐 Calling API: {test['method']} {test['url']}")

                response = requests.request(
                    method=test["method"],
                    url=test["url"],
                    json=test.get("payload", {}),
                    timeout=120  # 🔥 CRITICAL FIX
                )

                print(f"📡 Response Status: {response.status_code}")

                if response.status_code == test["expected_status"]:
                    result["status"] = "PASS"
                    print("✅ API Test Passed")
                else:
                    result["details"] = f"Expected {test['expected_status']}, got {response.status_code}"
                    print("❌ API Test Failed")

                text = f"""
                TEST NAME: {test['name']}
                METHOD: {test['method']}
                URL: {test['url']}
                EXPECTED: {test['expected_status']}
                ACTUAL: {response.status_code}
                RESULT: {result['status']}"""

                print("📸 Creating API screenshot...")

                screenshot_path = create_api_screenshot(
                    f"api_test_{index}",
                    text,
                    screenshot_folder
                )
                relative_path = screenshot_path.replace("\\", "/")
                screenshot_url = f"http://localhost:8000/{relative_path}"

                result["screenshots"] = [screenshot_url]
                result["steps"] = [
                    {
                        "type": "api",
                        "name": f"{test['method']} API",
                        "status": result["status"],
                        "message": f"Expected {test['expected_status']}, Got {response.status_code}",
                        "screenshot": screenshot_url
                    }
                ]
            # =========================
            # 🔹 UI TEST
            # =========================
            elif test["type"] == "ui":

                print("🌐 Starting UI Test...")
                print("📸 Screenshots Folder:", screenshot_folder)

                ui_start = time.time()

                try:
                     result = run_ui_with_timeout(test,screenshot_folder,TEST_TIMEOUT)
                except Exception as ui_error:
                     print("❌ UI RUNNER FAILED:", ui_error)
                     result = {
                         "name": test["name"],
                         "type": "ui",
                         "status": "FAIL",
                         "details": str(ui_error),
                         "screenshots": [],
                         "steps": [
                             {
                                 "type": "system",
                                 "name": "UI Runner Crash",
                                 "status": "FAIL",
                                 "message": str(ui_error),
                                 "screenshot": ""
                                }
                            ]
                        }
                
                # ✅ Ensure structure for Excel
                result.setdefault("screenshots", [])
                result.setdefault("steps", [])
                result.setdefault("details", "")
                result.setdefault("status", "FAIL")
                result.setdefault("name", test["name"])

                # ✅ Convert UI screenshot paths to URLs
                for step in result["steps"]:
                      if step.get("screenshot"):
                            relative_path = step["screenshot"].replace("\\", "/")
                            if "uploads/" in relative_path:
                                  relative_path = relative_path.split("uploads/")[1]
                                  step["screenshot"] = (f"http://localhost:8000/uploads/{relative_path}")
                # also update screenshots list
                updated_screenshots = []
                for shot in result["screenshots"]:
                      relative_path = shot.replace("\\", "/")
                      if "uploads/" in relative_path:
                            relative_path = relative_path.split("uploads/")[1]
                            shot = f"http://localhost:8000/uploads/{relative_path}"
                            updated_screenshots.append(shot)
                      result["screenshots"] = updated_screenshots

                # ⏱️ UI timeout check
                if time.time() - ui_start > TEST_TIMEOUT:
                    print("⏰ UI Test exceeded 5 mins → marking FAIL")
                    result["status"] = "FAIL"
                    result["details"] = "UI test timeout"

                print(f"📊 UI Result: {result['status']}")

            else:
                print("⚠️ Unknown test type")
                result["details"] = "Unknown test type"

        except requests.exceptions.Timeout:
            print("⏰ API Timeout (2  min )")
            result["details"] = "API timeout"

        except Exception as e:
            result["details"] = str(e)
            result["steps"].append({
                "type": "system",
                "name": "Execution Error",
                "status": "FAIL",
                "message": str(e),
                "screenshot": ""
            })
            print("❌ TEST ERROR:", e)
            

        duration = time.time() - start_time
        print(f"⏱️ Test completed in {round(duration,2)} sec")
        result["duration"] = duration

        if not result.get("steps"):
            result["steps"] = [
                {
                    "type": "system",
                    "name": "No Steps",
                    "status": "FAIL",
                    "message": "No execution steps captured",
                    "screenshot": ""
                }
            ]
        # 🤖 Generate AI analysis only for failed tests
        if result["status"] == "FAIL":
            result["ai_analysis"] = generate_failure_analysis(result)
        else:
            result["ai_analysis"] = "No issues detected"
        results.append(result)

    print("\n==============================")
    print("✅ ALL TESTS COMPLETED")
    print("==============================\n")

    return results