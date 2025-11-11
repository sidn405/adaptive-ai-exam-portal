"""
Enhanced transcription service with multiple provider support
Supports OpenAI Whisper API, Assembly AI, and local Whisper
"""

import os
import tempfile
from typing import Optional
from fastapi import UploadFile, HTTPException

# Import the media processing functions
from app.services.media_processor import process_media_file, validate_file_size, get_file_info


async def transcribe_audio(file: UploadFile) -> str:
    """
    Transcribe audio/video file to text using available transcription service
    Supports both audio and video files
    """
    # Validate file size (default 100MB limit)
    validate_file_size(file, max_size_mb=100)
    
    # Get file info
    file_info = get_file_info(file)
    print(f"Processing {file_info['file_type']} file: {file_info['filename']}")
    
    # Process media file (handles both audio and video)
    audio_bytes, audio_ext = await process_media_file(file)
    
    # Choose transcription method based on available services
    # Priority: OpenAI Whisper API > AssemblyAI > Local Whisper
    
    if os.getenv('OPENAI_API_KEY'):
        return await transcribe_with_openai_whisper(audio_bytes, audio_ext)
    elif os.getenv('ASSEMBLYAI_API_KEY'):
        return await transcribe_with_assemblyai(audio_bytes, audio_ext)
    else:
        return await transcribe_with_local_whisper(audio_bytes, audio_ext)


async def transcribe_with_openai_whisper(audio_bytes: bytes, extension: str) -> str:
    """Transcribe using OpenAI Whisper API"""
    try:
        import openai
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="OpenAI package not installed. Run: pip install openai"
        )
    
    try:
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Create temporary file for API upload
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name
        
        try:
            with open(temp_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            return transcript
        finally:
            os.unlink(temp_path)
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"OpenAI Whisper transcription failed: {str(e)}"
        )


async def transcribe_with_assemblyai(audio_bytes: bytes, extension: str) -> str:
    """Transcribe using AssemblyAI"""
    try:
        import requests
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Requests package not installed. Run: pip install requests"
        )
    
    try:
        api_key = os.getenv('ASSEMBLYAI_API_KEY')
        
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="ASSEMBLYAI_API_KEY environment variable not set"
            )
        
        # Upload file
        headers = {'authorization': api_key}
        upload_response = requests.post(
            'https://api.assemblyai.com/v2/upload',
            headers=headers,
            data=audio_bytes
        )
        upload_response.raise_for_status()
        audio_url = upload_response.json()['upload_url']
        
        # Request transcription
        transcript_response = requests.post(
            'https://api.assemblyai.com/v2/transcript',
            headers=headers,
            json={'audio_url': audio_url}
        )
        transcript_response.raise_for_status()
        transcript_id = transcript_response.json()['id']
        
        # Poll for completion
        import time
        while True:
            status_response = requests.get(
                f'https://api.assemblyai.com/v2/transcript/{transcript_id}',
                headers=headers
            )
            status_response.raise_for_status()
            status = status_response.json()
            
            if status['status'] == 'completed':
                return status['text']
            elif status['status'] == 'error':
                raise Exception(f"Transcription failed: {status.get('error')}")
            
            time.sleep(3)
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"AssemblyAI API request failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AssemblyAI transcription failed: {str(e)}"
        )


async def transcribe_with_local_whisper(audio_bytes: bytes, extension: str) -> str:
    """Transcribe using local Whisper model (fallback)"""
    raise HTTPException(
        status_code=500,
        detail="No transcription service configured. Please set ASSEMBLYAI_API_KEY or OPENAI_API_KEY environment variable. Local whisper is not installed."
    )


async def summarize_text(text: str) -> str:
    """Summarize text using AI"""
    return text[:500] + "..." if len(text) > 500 else text