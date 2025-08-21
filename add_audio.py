#!/usr/bin/env python3
"""
Add background audio to the Earth zoom-out video
"""

import numpy as np
from moviepy import VideoFileClip, AudioArrayClip, CompositeAudioClip
import os

def generate_ambient_audio(duration, sample_rate=44100):
    """Generate a simple ambient audio track"""
    
    # Generate time array
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create a gentle ambient soundscape
    # Base drone (low frequency)
    base_freq = 60  # Hz
    base_wave = 0.3 * np.sin(2 * np.pi * base_freq * t)
    
    # Add harmonics for richness
    harmonic1 = 0.2 * np.sin(2 * np.pi * base_freq * 2 * t)
    harmonic2 = 0.1 * np.sin(2 * np.pi * base_freq * 3 * t)
    
    # Add gentle high-frequency shimmer
    shimmer_freq = 800
    shimmer = 0.05 * np.sin(2 * np.pi * shimmer_freq * t) * np.sin(0.5 * t)
    
    # Add subtle wind-like noise
    wind = 0.02 * np.random.normal(0, 1, len(t))
    
    # Combine all elements
    audio = base_wave + harmonic1 + harmonic2 + shimmer + wind
    
    # Apply fade in and fade out
    fade_duration = 1.0  # seconds
    fade_samples = int(fade_duration * sample_rate)
    
    # Fade in
    fade_in = np.linspace(0, 1, fade_samples)
    audio[:fade_samples] *= fade_in
    
    # Fade out
    fade_out = np.linspace(1, 0, fade_samples)
    audio[-fade_samples:] *= fade_out
    
    # Normalize audio
    audio = audio / np.max(np.abs(audio)) * 0.3  # Keep volume moderate
    
    return audio

def add_audio_to_video(video_path, output_path):
    """Add generated audio to the video"""
    
    print("Loading video...")
    video = VideoFileClip(video_path)
    
    print("Generating ambient audio...")
    audio_array = generate_ambient_audio(video.duration)
    
    # Create audio clip
    audio_clip = AudioArrayClip(audio_array, fps=44100)
    
    print("Combining video and audio...")
    # Set audio to video
    final_video = video.with_audio(audio_clip)
    
    print("Writing final video with audio...")
    final_video.write_videofile(
        output_path,
        fps=30,
        codec='libx264',
        audio_codec='aac',
        preset='medium',
        ffmpeg_params=['-pix_fmt', 'yuv420p']
    )
    
    # Clean up
    video.close()
    final_video.close()
    
    print(f"✅ Video with audio saved to: {output_path}")

if __name__ == "__main__":
    input_video = "/workspace/earth_zoom_video.mp4"
    output_video = "/workspace/earth_zoom_video_with_audio.mp4"
    
    try:
        add_audio_to_video(input_video, output_video)
        print("\n🎵 Background audio added successfully!")
        print(f"📁 Final video: {output_video}")
        print("🎬 Ready for Instagram Reels upload!")
        
        # Show file sizes
        import os
        original_size = os.path.getsize(input_video) / (1024 * 1024)  # MB
        final_size = os.path.getsize(output_video) / (1024 * 1024)  # MB
        
        print(f"\n📊 File Sizes:")
        print(f"   Original (no audio): {original_size:.1f} MB")
        print(f"   Final (with audio): {final_size:.1f} MB")
        
    except Exception as e:
        print(f"❌ Error adding audio: {str(e)}")
        import traceback
        traceback.print_exc()