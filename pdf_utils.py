from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import os
from reportlab.lib import colors

def create_pdf(results, file_path):
    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("Test Report", styles['Title']))
    content.append(Spacer(1, 20))
    content.append(Paragraph("--------------------------------------------------", styles['Normal']))
    content.append(Spacer(1, 20))

    for test in results:
        status = test['status']
        color = "green" if status == "PASS" else "red"
        content.append(Paragraph(f"Test: {test['name']}", styles['Heading2']))
        content.append(Paragraph(f"Status: <font color='{color}'><b>{status}</b></font>", styles['Normal']))
        
        # ⏱️ NEW
        content.append(Paragraph(f"Execution Time: {round(test.get('duration', 0), 2)} sec", styles['Normal']))
        # Details
        details = test.get('details', '')
        if details:
            content.append(Paragraph(f"Details: {details}",styles['Normal']))
        
        # 🤖 AI analysis section
        ai_analysis = test.get("ai_analysis", "")
        if ai_analysis:
            content.append(Spacer(1,10))
            content.append(Paragraph("<b>AI Failure Analysis:</b>",styles['Heading3']))
            content.append(Paragraph(ai_analysis,styles['Normal']))
        content.append(Spacer(1, 10))

        # -------------------------
        # ✅ MULTIPLE SCREENSHOTS (IMPROVED)
        # -------------------------
        if test.get("screenshots"):
            content.append(Paragraph("Screenshots:",styles['Heading3']))
            for i, img_path in enumerate(test["screenshots"],start=1):
                try:
                    # convert URL back to local file
                    if img_path.startswith("http://localhost:8000/"):
                        img_path = img_path.replace("http://localhost:8000/","")
                        img_path = img_path.replace("/",os.sep)
                        
                        if os.path.exists(img_path):
                            content.append(Paragraph(f"Step {i}",styles['Normal']))
                            img = Image(img_path,width=450,height=250)
                            
                            content.append(img)
                            content.append(Spacer(1,10))
                except Exception as e:
                    content.append(Paragraph(f"Image load failed: {str(e)}",styles['Normal']))
        # -------------------------
        # ✅ SINGLE SCREENSHOT
        # -------------------------
        elif test.get("screenshot") and os.path.exists(test["screenshot"]):
            try:
                content.append(Paragraph("Screenshot:", styles['Heading3']))
                img = Image(test["screenshot"], width=450, height=250)
                content.append(img)
                content.append(Spacer(1, 10))
            except Exception as e:
                content.append(Paragraph(f"Image load failed: {str(e)}", styles['Normal']))

        # -------------------------
        # ✅ BACKWARD COMPATIBILITY (OLD SINGLE SCREENSHOT)
        # -------------------------
        elif test.get("screenshot") and os.path.exists(test["screenshot"]):
            try:
                img = Image(test["screenshot"], width=400, height=200)
                content.append(img)
                content.append(Spacer(1, 10))
            except Exception as e:
                content.append(Paragraph(f"Image load failed: {str(e)}", styles['Normal']))

        content.append(Spacer(1, 20))
        content.append(Paragraph("--------------------------------------------------", styles['Normal']))
        content.append(Spacer(1, 20))

    doc.build(content)