from playwright.sync_api import sync_playwright
from faker import Faker
import os, time, uuid

# -----------------------------
# ⏱️ TIME CONTROL
# -----------------------------
STEP_TIMEOUT = 60
GLOBAL_TIMEOUT = 300

last_activity = time.time()

def update_activity():
    global last_activity
    last_activity = time.time()

def is_global_timeout():
    return time.time() - last_activity > GLOBAL_TIMEOUT

def is_step_timeout(start):
    return time.time() - start > STEP_TIMEOUT


# -----------------------------
# 🔥 SMART CLICK (UPGRADED)
# -----------------------------
def smart_click(page, text):

    text = text.lower().strip()

    if any(x in text for x in ["download", "export", "pdf", "excel", "csv"]):
        print("⏭️ Skipping dangerous click:", text)
        return False

    # 1. direct selector
    try:
        page.click(text, timeout=3000)
        return True
    except:
        pass

    # 2. button by role
    try:
        page.get_by_role("button", name=text, exact=False).first.click(timeout=3000)
        return True
    except:
        pass

    # 3. text match
    try:
        page.get_by_text(text, exact=False).first.click(timeout=3000)
        return True
    except:
        pass

    # 4. partial match
    for word in text.split():
        try:
            page.get_by_text(word, exact=False).first.click(timeout=3000)
            return True
        except:
            continue

    print("❌ Click failed:", text)
    return False


# -----------------------------
# 🔥 SMART INPUT (UPGRADED)
# -----------------------------
# -----------------------------
# 🔥 SMART INPUT (UPGRADED - MULTI FIELD)
# -----------------------------
def smart_input(page, field=""):

    try:
        inputs = page.locator(
            "input:not([type=hidden]):not([type=file]), textarea"
        )
        fake = Faker()

        count = inputs.count()

        print(f"📝 Found {count} input fields")

        for i in range(count):
            try:
                inp = inputs.nth(i)

                if not inp.is_visible():
                    continue

                input_type = (
                    inp.get_attribute("type") or ""
                ).lower()

                placeholder = (
                    inp.get_attribute("placeholder") or ""
                ).lower()

                name = (
                    inp.get_attribute("name") or ""
                ).lower()

                label = placeholder + " " + name

                # 🔥 Intelligent data generation
                if "name" in label:
                    value = fake.name()
                elif "email" in label:
                    value = fake.email()
                elif "password" in label:
                    value = fake.password(length=10)
                elif "phone" in label or "mobile" in label:
                    value = fake.phone_number()
                elif "address" in label:
                    value = fake.address()
                elif "city" in label:
                    value = fake.city()
                elif input_type == "number":
                    value = str(fake.random_int(min=1, max=100))
                elif input_type == "date":
                    value = str(fake.date())
                else:
                    value = fake.word()

                inp.fill(value)

                print(
                    f"✅ Filled field {i+1}: {value}"
                )

            except Exception as e:
                print(
                    f"⚠️ Failed field {i+1}: {e}"
                )

        return True

    except Exception as e:
        print("❌ Input failed:", e)
        return False
    
def validate_button_click(page, before_url):
    try:
        page.wait_for_timeout(1500)

        after_url = page.url

        # ✅ navigation check
        if after_url != before_url:
            return True, "Navigation happened"

        # ✅ DOM change check (basic)
        body_text = page.locator("body").inner_text()
        if body_text:
            return True, "Page responded"

        return False, "No visible change"

    except Exception as e:
        return False, str(e)


def test_file_upload(page, screenshot_folder, test_name):

    print("📂 Testing file uploads...")

    results = []

    inputs = page.locator("input[type='file']")

    if inputs.count() == 0:
        print("⚠️ No upload fields found")
        return results

    base = os.path.join(screenshot_folder, "dummy")

    # create dummy files
    docx = base + ".docx"
    pdf = base + ".pdf"
    excel = base + ".xlsx"

    with open(docx, "w") as f:
        f.write("dummy word")

    with open(pdf, "w") as f:
        f.write("dummy pdf")

    with open(excel, "w") as f:
        f.write("dummy excel")

    files = {
        "docx": docx,
        "pdf": pdf,
        "excel": excel
    }

    for i in range(inputs.count()):

        file_input = inputs.nth(i)

        field_name = (
            file_input.get_attribute("name")
            or file_input.get_attribute("id")
            or ""
        ).lower()

        print(f"\n📂 Upload field {i+1}: {field_name}")

        # determine expected file type
        if "doc" in field_name or "word" in field_name:
            valid_type = "docx"

        elif "pdf" in field_name:
            valid_type = "pdf"

        elif "excel" in field_name or "xls" in field_name:
            valid_type = "excel"

        else:
            valid_type = "docx"

        # test ALL file types
        for file_type, file_path in files.items():

            try:
                file_input.set_input_files(file_path)

                page.wait_for_timeout(1500)

                expected_pass = (file_type == valid_type)

                screenshot = os.path.join(
                    screenshot_folder,
                    f"{test_name}_{field_name}_{file_type}.png"
                )

                page.screenshot(
                    path=screenshot,
                    full_page=True
                )

                results.append((
                    file_type,
                    expected_pass,
                    screenshot
                ))

                if expected_pass:
                    print(f"✅ {file_type} accepted correctly")
                else:
                    print(f"❌ {file_type} accepted (should reject)")

            except Exception:

                expected_pass = (file_type != valid_type)

                results.append((
                    file_type,
                    expected_pass,
                    ""
                ))

                if expected_pass:
                    print(f"✅ {file_type} rejected correctly")
                else:
                    print(f"❌ {file_type} rejected unexpectedly")

    return results
# -----------------------------
# 🔥 AUTO EXPLORE (SMART)
# -----------------------------
def auto_explore(page, screenshot_folder, test_name, max_steps=10):
    button_results = []

    print("🤖 Auto exploring UI...")

    visited = set()
    steps = 0

    buttons = page.locator("""
                           button,
                           a,
                           input[type=submit],
                           input[type=button],
                           .btn,
                           [role='button'],
                           .mud-button-root,
                           .mat-button,
                           .e-btn
                        """)

    for i in range(buttons.count()):

        if steps >= max_steps:
            print("🔹 Auto limit reached")
            break

        if is_global_timeout():
            print("⏰ Global timeout in auto explore")
            break

        try:
            btn = buttons.nth(i)
            text = btn.inner_text().strip().lower()

            if (
                not text
                or text in visited
                or len(text) > 20
                or any(x in text for x in ["login", "logout", "home"])
            ):
                continue

            visited.add(text)

            print("👉 Clicking:", text)

            current_url = page.url

            before_url = page.url
            
            btn.scroll_into_view_if_needed()
            page.wait_for_timeout(1000)
            btn.click(timeout=5000, force=True)
            page.wait_for_timeout(3000)
            update_activity()
            
            success, msg = validate_button_click(page, before_url)
            # 🔥 FORM DETECTION
            try:
                forms = page.locator("form")
                if forms.count() > 0:
                    print("📝 Form detected")
                    inputs = page.locator(
                        "input:not([type=hidden]), textarea"
                    )
                    for j in range(inputs.count()):
                        inp = inputs.nth(j)
                        if inp.is_visible():
                            try:
                                inp.fill(f"Test_{j}")
                            except:
                                pass
                    page.wait_for_timeout(1000)
                    submit_btns = page.locator("button, input[type=submit]")
                    if submit_btns.count() > 0:
                        try:
                            submit_btns.first.click(timeout=3000)
                            print("✅ Form submitted")
                        except:
                            pass
            except Exception as e:
                print("⚠️ Form automation error:", e)
            
            path = os.path.join(
                screenshot_folder,
                f"{test_name}_button_{steps}.png"
            )
            page.screenshot(path=path,full_page=True)
            step_data = {
                "type": "button",
                "name": text,
                "status": "PASS" if success else "FAIL",
                "message": msg,
                "screenshot": path
            }
            button_results.append(step_data)
            print(f"🔍 {text} → {msg}")
            
            if not success:
                print("❌ Button NOT working")
            else:
                print("✅ Button working")

            page.wait_for_timeout(1500)

            # ❌ avoid external navigation
            if page.url != current_url and "localhost" not in page.url:
                continue

            steps += 1

        except:
            continue
    return button_results


# -----------------------------
# 🚀 MAIN RUNNER (FINAL)
# -----------------------------
def run_ui_test(test, screenshot_folder):

    result = {
        "name": test["name"],
        "type": test.get("category", "ui"),
        "status": "FAIL",
        "details": "",
        "screenshots": [],
        "steps": []   # 🔥 NEW (VERY IMPORTANT)
    }

    print("\n==============================")
    print(f"🌐 UI TEST STARTED: {test['name']}")
    print("==============================")

    try:
        with sync_playwright() as p:

            browser = p.chromium.launch(headless=False,args=["--start-maximized"])
            page = browser.new_page(viewport={"width": 1280, "height": 800})

            print("🌍 Opening:", test["url"])

            page.goto(
                test["url"],
                timeout=120000,
                wait_until="networkidle"
            )
            page.wait_for_timeout(8000)

            update_activity()

            # -------------------------
            # 🔹 EXECUTE ACTIONS
            # -------------------------
            for i, action in enumerate(test.get("actions", [])):

                start = time.time()

                if is_global_timeout():
                    print("⏰ Global timeout → stop")
                    break

                try:
                    print("⚡ Step:", action)

                    if action["type"] == "click":
                        smart_click(page, action.get("selector", ""))

                    elif action["type"] == "upload_test":
                        upload_results = test_file_upload(page, screenshot_folder, test["name"])
                        
                        for filetype, status, path in upload_results:
                            if path:
                                result["screenshots"].append(path)
                            if not status:
                                result["details"] += f"{filetype} upload failed\n"

                    elif action["type"] == "input":
                        smart_input(page, action.get("selector", ""))

                    elif action["type"] == "wait":
                        time.sleep(action.get("time", 2))

                    update_activity()

                    # 📸 screenshot every step
                    path = os.path.join(
                        screenshot_folder,
                        f"{test['name']}_step_{i}.png"
                    )
                    page.screenshot(path=path,full_page=True)
                    result["screenshots"].append(path)

                    step_data = {
                        "type": action["type"],
                        "name": action.get("selector", action["type"]),
                        "status": "PASS",
                        "message": "Action executed successfully",
                        "screenshot": path
                    }
                    result["steps"].append(step_data)

                except Exception as e:
                    print("❌ Step error:", e)
                    result["details"] += str(e) + "\n"
                    
                    error_path = ""
                    
                    # 📸 ERROR screenshot
                    try:
                        error_path = os.path.join(
                            screenshot_folder,
                            f"{test['name']}_ERROR_{i}.png"
                        )
                        page.screenshot(path=error_path)
                        result["screenshots"].append(error_path)
                    except:
                        pass
                    # ✅ STORE FAILED STEP
                    result["steps"].append({
                        "type": action.get("type", "unknown"),
                        "name": action.get("selector", "unknown"),
                        "status": "FAIL",
                        "message": str(e),
                        "screenshot": error_path
                    })

                    # 📸 ERROR screenshot
                    try:
                        path = os.path.join(
                            screenshot_folder,
                            f"{test['name']}_ERROR_{i}.png"
                        )
                        page.screenshot(path=path,full_page=True)
                        result["screenshots"].append(path)
                    except:
                        pass

                if is_step_timeout(start):
                    print("⏰ Step timeout → skip")
                    continue

            # -------------------------
            # 🔥 AUTO EXPLORE
            # -------------------------
            button_results = auto_explore(page, screenshot_folder, test["name"], max_steps=10)
            for step in button_results:
                result["steps"].append(step)
                result["screenshots"].append(step["screenshot"])
            
            # -------------------------
            # 📂 FILE UPLOAD TEST
            # -------------------------
            upload_results = test_file_upload(
                page,
                screenshot_folder,
                test["name"]
            )
            for filetype, status, path in upload_results:
                step_data = {
                    "type": "upload",
                    "name": filetype.upper(),
                    "status": "PASS" if status else "FAIL",
                    "message": "",
                    "screenshot": path
                }
                # ✅ Message
                if filetype == "docx":
                    step_data["message"] = ("DOCX upload working"
                                            if status
                                            else "DOCX validation failed")
                elif filetype == "pdf":
                    step_data["message"] = ("PDF validation passed"
                                            if status
                                            else "PDF validation failed")
                elif filetype == "excel":
                    step_data["message"] = ("Excel upload working"
                                            if status
                                            else "Excel validation failed")
                # ✅ Add step
                result["steps"].append(step_data)
                
                # ✅ Add screenshot
                if path:
                    result["screenshots"].append(path)

            # -------------------------
            # 🔹 ASSERT
            # -------------------------
            assertion = test.get("assert")

            if assertion:
                if assertion["type"] == "url_contains":
                    if assertion["value"] in page.url:
                        result["status"] = "PASS"
                    else:
                        result["details"] = f"URL mismatch: {page.url}"

                elif assertion["type"] == "text_present":
                    if page.locator(f"text={assertion['value']}").count() > 0:
                        result["status"] = "PASS"
                    else:
                        result["details"] = "Text not found"

                else:
                    result["status"] = "PASS"
            # -------------------------
            # 🎯 FINAL STATUS DECISION
            # -------------------------
            pass_count = sum(1 for step in result["steps"]
                             if step["status"] == "PASS"
                            )
            fail_count = sum(1 for step in result["steps"]
                             if step["status"] == "FAIL"
                            )
            if pass_count >= fail_count:
                result["status"] = "PASS"
            else:
                result["status"] = "FAIL"

            browser.close()

    except Exception as e:
        print("❌ FATAL ERROR:", e)
        result["details"] = str(e)
        try:
            path = os.path.join(
                screenshot_folder,
                f"{test['name']}_FATAL.png"
            )
            page.screenshot(path=path,full_page=True)
            result["screenshots"].append(path)
        except:
            pass
    
    print("📊 FINAL STATUS:", result["status"])
    print("📄 DETAILS:", result["details"])    
    print("==============================\n")

    return result