#!/usr/bin/env python3
"""
Test script for custom template preview endpoints
"""
import requests
import json

# Test data
test_template_content = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Template Preview</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
    </style>
</head>
<body>
    <h1>Template de Prueba</h1>
    <p>Esta es una preview de template personalizado.</p>
</body>
</html>
"""

def test_preview_generation():
    """Test the custom template preview generation endpoint"""
    url = "http://localhost:8000/api/custom-templates/preview"

    payload = {
        "templateId": "test-template",
        "templateContent": test_template_content
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")

        if response.status_code == 200:
            data = response.json()
            if "preview_url" in data:
                preview_url = data["preview_url"]
                print(f"✅ Preview URL generated: {preview_url}")

                # Test accessing the preview
                preview_response = requests.get(preview_url, timeout=10)
                print(f"Preview access status: {preview_response.status_code}")
                if preview_response.status_code == 200:
                    print("✅ Preview accessible")
                    print(f"Content length: {len(preview_response.text)} chars")
                else:
                    print("❌ Preview not accessible")
            else:
                print("❌ No preview_url in response")
        else:
            print("❌ Preview generation failed")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Testing custom template preview endpoints...")
    test_preview_generation()