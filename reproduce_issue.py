import requests
import json
import base64
import os
import sys

# Configuration
BASE_URL = "http://localhost:8080"  # Assuming running locally via gunicorn or python
# If running against production:
# BASE_URL = "https://google-ads-backend-mm4z.onrender.com"

def create_dummy_image():
    # Create a tiny 1x1 pixel transparent GIF or similar base64
    return "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"

def test_full_generation():
    print("🚀 Starting Full Feature Test...")
    
    # 1. Define Payload with ALL features
    payload = {
        "customerId": "1234567890",
        "adGroupId": "1234567890",
        "whatsappNumber": "+573001234567",
        "gtmId": "GTM-TEST1234",
        "phoneNumber": "+573001234567",
        "selectedTemplate": "base.html", # User said they selected this
        "useDynamicDesign": True,        # User said they selected automatic design
        "layoutStyle": "auto",
        "optimizeImagesWithAI": False,
        "selectedColorPalette": "mystical",
        
        # User Images (All positions)
        "userImages": [
            {"position": "top", "url": "https://via.placeholder.com/800x400?text=TOP+IMAGE"},
            {"position": "middle", "url": "https://via.placeholder.com/800x400?text=MIDDLE+IMAGE"},
            {"position": "bottom", "url": "https://via.placeholder.com/800x400?text=BOTTOM+IMAGE"},
            {"position": "hero_bg", "url": "https://via.placeholder.com/1920x1080?text=HERO+BG"},
            {"position": "benefits", "url": "https://via.placeholder.com/400x400?text=BENEFITS"},
            {"position": "promo", "url": "https://via.placeholder.com/800x400?text=PROMO"},
            {"position": "cta1", "url": "https://via.placeholder.com/400x400?text=CTA1"},
            {"position": "cta2", "url": "https://via.placeholder.com/400x400?text=CTA2"}
        ],
        
        # User Video
        "userVideos": [
            {"url": "https://www.w3schools.com/html/mov_bbb.mp4", "position": "hero"}
        ],
    }
    
    print("📦 Payload prepared with:")
    print(f"   - {len(payload['userImages'])} Images")
    print(f"   - {len(payload['userVideos'])} Videos")
    print(f"   - Dynamic Design: {payload['useDynamicDesign']}")
    
    # 2. Mock the API call locally by invoking the generator directly
    # This avoids needing the server running and allows inspecting the HTML output directly
    
    try:
        sys.path.append(os.getcwd())
        from landing_generator import LandingPageGenerator
        from unittest.mock import MagicMock, patch
        
        # Mock Google Ads Client
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        
        # Mock Context Extraction to return dummy data
        # We need to patch extract_ad_group_context or the methods it calls
        # For simplicity, let's instantiate the generator and mock the run method's internal steps if possible
        # Or better, let's just run it and mock the network calls
        
        gen = LandingPageGenerator(google_ads_client_provider=lambda: mock_client)
        
        # Mock internal methods to avoid real API calls
        gen._extract_keywords = MagicMock(return_value=["amarres de amor", "hechizos", "retorno de pareja"])
        gen._extract_ad_content = MagicMock(return_value=(["Headline 1", "Headline 2"], ["Desc 1", "Desc 2"]))
        gen._extract_locations = MagicMock(return_value=["Bogota", "Medellin"])
        gen.generate_content = MagicMock(return_value=MagicMock(
            headline="Headline Generado",
            subheadline="Subheadline Generado",
            intro_paragraph="<p>Intro paragraph content.</p>",
            body_paragraph="<p>Body paragraph content.</p>",
            closing_headline="Closing Headline",
            closing_paragraph="Closing Paragraph",
            benefits=["Benefit 1", "Benefit 2", "Benefit 3"],
            testimonials=[{"name": "User", "text": "Testimonial"}],
            cta_text="Call Now"
        ))
        gen.publish_as_github_pages = MagicMock(return_value={"url": "http://mock.url", "alias": "mock-alias", "commit_sha": "123"})
        gen.publish_to_github = MagicMock(side_effect=lambda path, content: f"https://cdn.jsdelivr.net/gh/mockuser/mockrepo/{path}")
        gen.upload_asset_to_github = MagicMock(side_effect=lambda content, filename: f"https://cdn.jsdelivr.net/gh/mockuser/mockrepo/assets/images/{filename}")
        gen._verify_asset_availability = MagicMock(return_value=True)
        gen.health_check = MagicMock(return_value=True)
        gen.update_final_urls = MagicMock(return_value=True)
        
        # Mock requests.get to avoid download errors
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Return a valid 1x1 GIF bytes
        mock_response.content = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
        
        with patch('requests.get', return_value=mock_response):
            # Run generation
            print("🔄 Running Generator...")
            result = gen.run(
                customer_id=payload["customerId"],
                ad_group_id=payload["adGroupId"],
                whatsapp_number=payload["whatsappNumber"],
                gtm_id=payload["gtmId"],
                user_images=payload["userImages"],
                user_videos=payload["userVideos"],
                use_dynamic_design=payload["useDynamicDesign"],
                layout_style=payload["layoutStyle"]
            )
        
        print("✅ Generation completed!")
        
        # Now we need to inspect the HTML that was "published"
        # Since we mocked publish_as_github_pages, we can get the HTML from the call args
        html_content = gen.publish_as_github_pages.call_args[0][1]
        
        # 3. Analyze HTML
        print("\n🔍 Analyzing Generated HTML...")
        
        # Check for Images
        missing_images = []
        found_images = []
        
        # We need to check for the PROCESSED URLs (CDN), not the original ones
        # Since we mocked the upload, we know the pattern
        cdn_base = "https://cdn.jsdelivr.net/gh/mockuser/mockrepo/assets/images/"
        
        if cdn_base in html_content:
            print(f"✅ Found CDN images in HTML!")
            # Count occurrences
            count = html_content.count(cdn_base)
            print(f"   - Count: {count}")
        else:
            print(f"❌ No CDN images found in HTML")

        # Check for Video
        # Video URL is passed directly if not processed/uploaded (or if mocked)
        # In our payload: "https://www.w3schools.com/html/mov_bbb.mp4"
        video_url = payload["userVideos"][0]["url"]
        if video_url in html_content:
            print("🎥 Video Found: YES")
        else:
            print("❌ Video Found: NO")
            
        # Save HTML for manual inspection
        with open("debug_output.html", "w") as f:
            f.write(html_content)
        print("\n💾 Saved HTML to debug_output.html")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_full_generation()
