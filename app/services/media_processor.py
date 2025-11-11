"""
Audio and Video processing service for lecture transcription
Supports: MP3, WAV, M4A, WebM (audio) and MP4, AVI, MOV, WebM (video)
"""

import os
import tempfile
from typing import Optional
from fastapi import UploadFile, HTTPException
import subprocess
import shutil

# Check if ffmpeg is available (required for video processing)
def check_ffmpeg():
    return shutil.which('ffmpeg') is not None

# Extract audio from video file
async def extract_audio_from_video(video_file: UploadFile) -> str:
    """
    Extract audio from video file using ffmpeg
    Returns path to extracted audio file
    """
    if not check_ffmpeg():
        raise HTTPException(
            status_code=500,
            detail="ffmpeg not installed. Install with: apt-get install ffmpeg (Linux) or brew install ffmpeg (Mac)"
        )
    
    # Create temporary files
    video_temp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(video_file.filename)[1])
    audio_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    
    try:
        # Save uploaded video
        content = await video_file.read()
        video_temp.write(content)
        video_temp.close()
        
        # Extract audio using ffmpeg
        command = [
            'ffmpeg',
            '-i', video_temp.name,
            '-vn',  # no video
            '-acodec', 'pcm_s16le',  # audio codec
            '-ar', '16000',  # sample rate
            '-ac', '1',  # mono channel
            audio_temp.name,
            '-y'  # overwrite output file
        ]
        
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        
        audio_temp.close()
        return audio_temp.name
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract audio from video: {e.stderr.decode()}"
        )
    finally:
        # Cleanup video file
        try:
            os.unlink(video_temp.name)
        except:
            pass


# Process audio/video file for transcription
async def process_media_file(file: UploadFile) -> tuple[bytes, str]:
    """
    Process uploaded media file (audio or video)
    Returns: (audio_bytes, file_extension)
    """
    filename = file.filename.lower()
    
    # Video formats - extract audio first
    video_formats = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']
    if any(filename.endswith(fmt) for fmt in video_formats):
        audio_path = await extract_audio_from_video(file)
        try:
            with open(audio_path, 'rb') as f:
                audio_bytes = f.read()
            return audio_bytes, '.wav'
        finally:
            os.unlink(audio_path)
    
    # Audio formats - use directly
    audio_formats = ['.mp3', '.wav', '.m4a', '.webm', '.ogg', '.flac']
    if any(filename.endswith(fmt) for fmt in audio_formats):
        audio_bytes = await file.read()
        ext = os.path.splitext(filename)[1]
        return audio_bytes, ext
    
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported file format. Supported: {', '.join(audio_formats + video_formats)}"
    )


# Validate file size
def validate_file_size(file: UploadFile, max_size_mb: int = 200): #Adjust file size
    """Validate uploaded file size"""
    if hasattr(file, 'size') and file.size:
        size_mb = file.size / (1024 * 1024)
        if size_mb > max_size_mb:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {max_size_mb}MB, uploaded: {size_mb:.1f}MB"
            )


# Get file info
def get_file_info(file: UploadFile) -> dict:
    """Get information about uploaded file"""
    filename = file.filename.lower()
    
    video_formats = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']
    audio_formats = ['.mp3', '.wav', '.m4a', '.webm', '.ogg', '.flac']
    
    if any(filename.endswith(fmt) for fmt in video_formats):
        file_type = 'video'
    elif any(filename.endswith(fmt) for fmt in audio_formats):
        file_type = 'audio'
    else:
        file_type = 'unknown'
    
    return {
        'filename': file.filename,
        'content_type': file.content_type,
        'file_type': file_type,
        'extension': os.path.splitext(file.filename)[1]
    }