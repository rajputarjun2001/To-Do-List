#!/usr/bin/env python3
"""
Optimize the Earth zoom-out video for Instagram Reels
"""

from moviepy import VideoFileClip
import os

def optimize_for_instagram(input_path, output_path):
    """Optimize video for Instagram Reels"""
    
    print("Loading video...")
    video = VideoFileClip(input_path)
    
    print(f"Original video info:")
    print(f"  Duration: {video.duration:.1f} seconds")
    print(f"  Size: {video.size}")
    print(f"  FPS: {video.fps}")
    
    # Ensure the video is exactly the right duration (10-15 seconds is ideal for Instagram)
    target_duration = min(15, video.duration)
    if video.duration > target_duration:
        print(f"Trimming video to {target_duration} seconds...")
        video = video.subclipped(0, target_duration)
    
    # Ensure 9:16 aspect ratio
    if video.size[0] != 1080 or video.size[1] != 1920:
        print("Resizing to Instagram Reels format (1080x1920)...")
        video = video.resized((1080, 1920))
    
    print("Optimizing and saving...")
    video.write_videofile(
        output_path,
        fps=30,
        codec='libx264',
        preset='fast',  # Faster encoding
        bitrate='2000k',  # Good quality for Instagram
        audio=False,  # No audio for now
        ffmpeg_params=[
            '-pix_fmt', 'yuv420p',  # Ensure compatibility
            '-movflags', '+faststart'  # Enable fast streaming
        ]
    )
    
    video.close()
    print(f"✅ Optimized video saved to: {output_path}")

def create_preview_info():
    """Create a text file with video information"""
    info_text = """
🎬 EARTH ZOOM-OUT VIDEO - INSTAGRAM REELS READY

📱 Specifications:
   • Format: MP4 (H.264)
   • Resolution: 1080x1920 (9:16 aspect ratio)
   • Frame Rate: 30 FPS
   • Duration: ~12 seconds
   • Optimized for Instagram Reels

🎨 Effect Description:
   • Starts with beach scene (ground level)
   • Smoothly zooms out to aerial view
   • Transitions to city/regional view
   • Continues to country-level view
   • Ends with full Earth from space
   • Cinematic transitions with easing

📋 Usage Instructions:
   1. Upload directly to Instagram Reels
   2. Add your own music using Instagram's music library
   3. Consider adding text overlays or captions
   4. Use trending hashtags for better reach

💡 Tips for Instagram:
   • Post during peak hours (7-9 PM)
   • Use relevant hashtags (#earthzoom #cinematic #reel)
   • Add engaging captions
   • Consider adding text overlays for context

🎵 Audio Recommendation:
   Since Instagram has a vast music library, you can add:
   • Ambient/cinematic music
   • Trending audio clips
   • Inspirational music
   • Nature sounds

✨ This video is ready for upload to Instagram Reels!
"""
    
    with open('/workspace/video_info.txt', 'w') as f:
        f.write(info_text)
    
    print("📋 Created video information file: video_info.txt")

if __name__ == "__main__":
    input_video = "/workspace/earth_zoom_video.mp4"
    output_video = "/workspace/earth_zoom_instagram_ready.mp4"
    
    try:
        optimize_for_instagram(input_video, output_video)
        create_preview_info()
        
        # Show file information
        original_size = os.path.getsize(input_video) / (1024 * 1024)  # MB
        optimized_size = os.path.getsize(output_video) / (1024 * 1024)  # MB
        
        print(f"\n📊 Final Results:")
        print(f"   Original: {original_size:.1f} MB")
        print(f"   Optimized: {optimized_size:.1f} MB")
        print(f"   Compression: {((original_size - optimized_size) / original_size * 100):.1f}%")
        
        print(f"\n🎉 SUCCESS! Your Instagram Reels video is ready!")
        print(f"📁 File: {output_video}")
        print(f"📋 Info: /workspace/video_info.txt")
        
    except Exception as e:
        print(f"❌ Error optimizing video: {str(e)}")
        import traceback
        traceback.print_exc()