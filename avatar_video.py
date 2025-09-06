import requests
import time
import os

def check_and_download_video(api_key, video_id, output_filename="generated_video.mp4"):
    """
    Check video status and download when completed
    
    Args:
        api_key (str): Your HeyGen API key
        video_id (str): Video ID to monitor
        output_filename (str): Local filename for downloaded video
    """
    
    # Setup headers for API requests
    headers = {
        'X-Api-Key': api_key
    }
    
    # Construct the video status URL
    video_status_url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
    
    print(f"🎬 Monitoring Video ID: {video_id}")
    print(f"📁 Will save as: {output_filename}")
    print("=" * 50)
    
    check_count = 0
    
    while True:
        check_count += 1
        print(f"🔍 Check #{check_count} - Getting video status...")
        
        try:
            # Get video status
            response = requests.get(video_status_url, headers=headers)
            
            if response.status_code != 200:
                print(f"❌ API Error: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                break
            
            # Parse response
            response_data = response.json()
            status = response_data["data"]["status"]
            
            print(f"📊 Current Status: {status.upper()}")
            
            if status == "completed":
                # Video is ready!
                video_url = response_data["data"]["video_url"]
                thumbnail_url = response_data["data"]["thumbnail_url"]
                
                print("🎉 Video generation completed!")
                print(f"📹 Video URL: {video_url}")
                print(f"🖼️  Thumbnail URL: {thumbnail_url}")
                print()
                
                # Download the video
                print(f"📥 Downloading video as '{output_filename}'...")
                
                try:
                    video_response = requests.get(video_url)
                    video_response.raise_for_status()
                    video_content = video_response.content
                    
                    # Save video to file
                    with open(output_filename, "wb") as video_file:
                        video_file.write(video_content)
                    
                    file_size_mb = len(video_content) / (1024 * 1024)
                    print(f"✅ Video downloaded successfully!")
                    print(f"📁 File: {output_filename}")
                    print(f"📏 Size: {file_size_mb:.2f} MB")
                    
                    # Also save thumbnail if available
                    if thumbnail_url:
                        try:
                            thumb_response = requests.get(thumbnail_url)
                            thumb_filename = f"thumbnail_{video_id}.jpg"
                            with open(thumb_filename, "wb") as thumb_file:
                                thumb_file.write(thumb_response.content)
                            print(f"🖼️  Thumbnail saved: {thumb_filename}")
                        except Exception as e:
                            print(f"⚠️  Couldn't save thumbnail: {str(e)}")
                    
                except Exception as e:
                    print(f"❌ Download failed: {str(e)}")
                
                break
                
            elif status == "processing" or status == "pending" or status == "waiting":
                # Video is still being processed
                status_messages = {
                    "processing": "🔄 Video is being generated...",
                    "pending": "📋 Video is queued for processing...",
                    "waiting": "⏳ Video is waiting to start..."
                }
                
                print(status_messages.get(status, f"🔄 Video is {status}..."))
                print("⏰ Checking again in 5 seconds...")
                print()
                
                time.sleep(5)  # Wait 5 seconds before checking again
                
            elif status == "failed":
                # Video generation failed
                error = response_data["data"].get("error", "Unknown error")
                print(f"❌ Video generation failed: '{error}'")
                break
                
            else:
                # Unknown status
                print(f"❓ Unknown status: {status}")
                print("🔄 Continuing to monitor...")
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\n⏸️  Monitoring stopped by user")
            print(f"Video {video_id} may still be processing")
            break
            
        except Exception as e:
            print(f"❌ Error checking status: {str(e)}")
            print("🔄 Retrying in 10 seconds...")
            time.sleep(10)

def main():
    """
    Main function with your specific video details
    """
    # Your API credentials and video ID
    API_KEY = ""
    VIDEO_ID = ""  # Your latest video
    
    print("🎬 HeyGen Video Processor")
    print("=" * 30)
    
    # Check and download the video
    check_and_download_video(
        api_key=API_KEY,
        video_id=VIDEO_ID,
        output_filename=f"heygen_video_{VIDEO_ID}.mp4"
    )

def process_custom_video(api_key, video_id, filename=None):
    """
    Process any video ID with custom filename
    """
    if filename is None:
        filename = f"video_{video_id}.mp4"
    
    check_and_download_video(api_key, video_id, filename)

if __name__ == "__main__":
    # Run with your specific video
    main()
    
    # Uncomment below to process a different video:
    # API_KEY = "your-api-key"
    # process_custom_video(API_KEY, "different-video-id", "custom_name.mp4")