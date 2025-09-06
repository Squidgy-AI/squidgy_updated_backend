import requests
import json
import time

def test_your_avatar():
    """
    Test your specific avatar ID and API key
    """
    API_KEY = ""
    AVATAR_ID = ""
    
    url = "https://api.heygen.com/v2/video/generate"
    
    headers = {
        'X-Api-Key': API_KEY,
        'Content-Type': 'application/json'
    }
    
    payload = {
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": AVATAR_ID,
                    "avatar_style": "normal"
                },
                "voice": {
                    "type": "text",
                    "input_text": "Hello Seth this is Soma your avatar is working fine!!.",
                    "voice_id": "e7fc27869cdb47559a044020fd663fac"
                },
                "background": {
                    "type": "color",
                    "value": "#4A90E2"
                }
            }
        ],
        "dimension": {
            "width": 1280,
            "height": 720
        }
    }
    
    print("🎭 Testing Your Custom Avatar")
    print("=" * 40)
    print(f"🆔 Avatar ID: {AVATAR_ID}")
    print(f"🔑 API Key: {API_KEY[:20]}...")
    print()
    
    try:
        print("📡 Making API request...")
        response = requests.post(url, headers=headers, json=payload)
        
        print(f"📊 HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            video_id = result.get("data", {}).get("video_id")
            
            print("✅ SUCCESS! Your avatar is working perfectly!")
            print(f"🎬 New Video ID: {video_id}")
            print()
            print("🔄 Now let's check the video status...")
            
            # Check status immediately
            check_video_status(API_KEY, video_id)
            
            return video_id
            
        elif response.status_code == 400:
            print("❌ Bad Request - Let's see the details:")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2))
                
                # Check if it's an avatar ID issue
                error_msg = str(error_data).lower()
                if 'avatar' in error_msg or 'character' in error_msg:
                    print("\n💡 This looks like an avatar ID issue.")
                    print("Your avatar ID might be:")
                    print("1. Invalid or expired")
                    print("2. Not accessible with your current plan")
                    print("3. Requires different formatting")
                    
            except:
                print(f"Raw error response: {response.text}")
                
        elif response.status_code == 401:
            print("❌ Unauthorized - API key issue")
            
        else:
            print(f"❌ Unexpected error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        
    return None

def check_video_status(api_key, video_id):
    """
    Check video status using multiple endpoints
    """
    endpoints = [
        ("v1/video_status.get", f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"),
        ("v2/video/{id}", f"https://api.heygen.com/v2/video/{video_id}"),
        ("v1/video/{id}", f"https://api.heygen.com/v1/video/{video_id}")
    ]
    
    headers = {'X-Api-Key': api_key}
    
    for name, url in endpoints:
        try:
            print(f"🔍 Trying {name}...")
            
            if "video_status.get" in url:
                response = requests.get("https://api.heygen.com/v1/video_status.get", 
                                      headers=headers, 
                                      params={"video_id": video_id})
            else:
                response = requests.get(url, headers=headers)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                data = result.get("data", {})
                status = data.get("status", "unknown")
                
                print(f"   ✅ Working! Video status: {status}")
                
                if status == "completed":
                    video_url = data.get("video_url")
                    if video_url:
                        print(f"   🎉 Video ready: {video_url}")
                        
                return result
                
            else:
                print(f"   ❌ Error: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")
    
    print("⚠️ No working status endpoint found")
    return None

def test_fallback_avatars(api_key):
    """
    Test some known working avatar IDs as fallback
    """
    fallback_avatars = [
        "Daisy-inskirt-20220818",
        "josh_lite3_20230714", 
        "Anna_public_3_20240108"
    ]
    
    print("\n🔄 Testing fallback avatars...")
    
    for avatar_id in fallback_avatars:
        print(f"\n🧪 Testing: {avatar_id}")
        
        if test_single_avatar(api_key, avatar_id):
            print(f"✅ {avatar_id} works as fallback!")
            return avatar_id
        else:
            print(f"❌ {avatar_id} failed")
    
    return None

def test_single_avatar(api_key, avatar_id):
    """
    Quick test of a single avatar
    """
    url = "https://api.heygen.com/v2/video/generate"
    headers = {'X-Api-Key': api_key, 'Content-Type': 'application/json'}
    
    payload = {
        "video_inputs": [{
            "character": {"type": "avatar", "avatar_id": avatar_id, "avatar_style": "normal"},
            "voice": {"type": "text", "input_text": f"Testing avatar {avatar_id}", "voice_id": "2d5b0e6cf36f460aa7fc47e3eee4ba54"},
            "background": {"type": "color", "value": "#008000"}
        }],
        "dimension": {"width": 1280, "height": 720}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        return response.status_code == 200
    except:
        return False

if __name__ == "__main__":
    print("🎭 HeyGen Avatar Test Suite")
    print("Testing your specific avatar and API setup")
    print("=" * 50)
    
    # Test your specific avatar
    video_id = test_your_avatar()

    print(video_id)
    
    # if not video_id:
    #     print("\n" + "="*30)
    #     print("🔄 Your custom avatar didn't work.")
    #     print("Let's test some known working avatars...")
        
    #     API_KEY = "NzQ5MTY5M2Q4YTJkNGZlMTgyNDlhNWY1NzcwMDBkMjAtMTczNDg5ODg2OQ=="
    #     working_avatar = test_fallback_avatars(API_KEY)
        
    #     if working_avatar:
    #         print(f"\n✅ You can use '{working_avatar}' as a working avatar!")
    #     else:
    #         print("\n❌ No avatars worked. Check your API key and account status.")