#!/usr/bin/env python3
import argparse
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip

def add_background_music(input_video_path: str,
                         background_audio_path: str,
                         output_video_path: str,
                         music_volume: float = 0.3):
    """
    Adds background music to a video while preserving original audio.

    Args:
        input_video_path: Path to the source video (with voice).
        background_audio_path: Path to drum-heavy background music.
        output_video_path: Path for the processed output video.
        music_volume: Relative volume for the background track (0.0–1.0).
    """
    # Load the video
    video = VideoFileClip(input_video_path)  # 9
    original_audio = video.audio           # 10

    # Load and adjust background music
    bg_music = AudioFileClip(background_audio_path) \
               .volumex(music_volume)      # 11
    bg_music = bg_music.set_duration(video.duration)

    # Composite original audio and background music
    final_audio = CompositeAudioClip([original_audio, bg_music])  # 12

    # Set composite audio back onto the video
    video_with_music = video.set_audio(final_audio)

    # Export final video
    video_with_music.write_videofile(
        output_video_path,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="temp-audio.m4a",
        remove_temp=True
    )  # 13

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Add drum-heavy background music to a video, preserving the original voice."
    )
    parser.add_argument("input_video", help="Path to input video file (e.g., VID-20250509-WA0020.mp4)")
    parser.add_argument("background_audio", help="Path to background music file (e.g., drums.mp3)")
    parser.add_argument("output_video", help="Desired path for output video file")
    parser.add_argument(
        "--music_volume",
        type=float,
        default=0.3,
        help="Volume level for background music (0.0–1.0; lower = subtler)"
    )

    args = parser.parse_args()
    add_background_music(
        args.input_video,
        args.background_audio,
        args.output_video,
        args.music_volume
    )
