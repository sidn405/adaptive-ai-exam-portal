from fastapi import UploadFile
import os
import time
from typing import Optional


async def transcribe_audio(file: UploadFile) -> str:
    """
    Transcribe audio file to text using AssemblyAI.
    """
    # Read file content
    content = await file.read()
    filename = file.filename or "audio_file"
    file_size = len(content)
    
    # Check for AssemblyAI API key
    api_key = os.environ.get("ASSEMBLYAI_API_KEY")
    
    if api_key:
        try:
            print(f"Transcribing {filename} with AssemblyAI...")
            return await transcribe_with_assemblyai(content, filename, api_key)
        except Exception as e:
            print(f"AssemblyAI transcription failed: {e}")
            print("Falling back to placeholder transcription")
            return generate_placeholder_transcript(filename, file_size)
    else:
        print("No ASSEMBLYAI_API_KEY found, using placeholder transcription")
        return generate_placeholder_transcript(filename, file_size)


async def transcribe_with_assemblyai(content: bytes, filename: str, api_key: str) -> str:
    """
    Transcribe using AssemblyAI API.
    """
    try:
        import assemblyai as aai
    except ImportError:
        raise Exception("AssemblyAI library not installed. Run: pip install assemblyai")
    
    # Configure AssemblyAI
    aai.settings.api_key = api_key
    
    # Create temporary file
    import tempfile
    
    # Get file extension
    extension = filename.split('.')[-1] if '.' in filename else 'mp3'
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{extension}') as temp_file:
        temp_file.write(content)
        temp_path = temp_file.name
    
    try:
        # Create transcriber
        transcriber = aai.Transcriber()
        
        print(f"Uploading {filename} to AssemblyAI...")
        
        # Transcribe the file
        transcript = transcriber.transcribe(temp_path)
        
        # Wait for transcription to complete
        if transcript.status == aai.TranscriptStatus.error:
            raise Exception(f"Transcription failed: {transcript.error}")
        
        print(f"✓ Transcribed {filename} successfully")
        print(f"  Duration: {transcript.audio_duration}s")
        print(f"  Words: {len(transcript.words) if transcript.words else 0}")
        
        return transcript.text
        
    finally:
        # Clean up temp file
        import os
        if os.path.exists(temp_path):
            os.remove(temp_path)


async def transcribe_with_assemblyai_advanced(
    content: bytes, 
    filename: str, 
    api_key: str,
    speaker_labels: bool = False,
    auto_chapters: bool = False
) -> str:
    """
    Advanced transcription with speaker diarization and chapters.
    """
    try:
        import assemblyai as aai
    except ImportError:
        raise Exception("AssemblyAI library not installed")
    
    # Configure AssemblyAI
    aai.settings.api_key = api_key
    
    # Create temporary file
    import tempfile
    extension = filename.split('.')[-1] if '.' in filename else 'mp3'
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{extension}') as temp_file:
        temp_file.write(content)
        temp_path = temp_file.name
    
    try:
        # Configure transcription
        config = aai.TranscriptionConfig(
            speaker_labels=speaker_labels,
            auto_chapters=auto_chapters,
            punctuate=True,
            format_text=True
        )
        
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(temp_path, config=config)
        
        if transcript.status == aai.TranscriptStatus.error:
            raise Exception(f"Transcription failed: {transcript.error}")
        
        # Format output
        output = transcript.text
        
        # Add speaker labels if enabled
        if speaker_labels and transcript.utterances:
            output = "\n\n=== Transcription with Speaker Labels ===\n\n"
            for utterance in transcript.utterances:
                output += f"Speaker {utterance.speaker}: {utterance.text}\n\n"
        
        # Add chapters if enabled
        if auto_chapters and transcript.chapters:
            output += "\n\n=== Chapters ===\n\n"
            for chapter in transcript.chapters:
                output += f"Chapter: {chapter.headline}\n"
                output += f"Summary: {chapter.summary}\n\n"
        
        print(f"✓ Advanced transcription complete")
        return output
        
    finally:
        import os
        if os.path.exists(temp_path):
            os.remove(temp_path)


def generate_placeholder_transcript(filename: str, file_size: int) -> str:
    """
    Generate placeholder when API key not available.
    """
    transcript = f"""This is a placeholder transcription for: {filename}

File size: {file_size / 1024:.1f} KB

To enable real AssemblyAI transcription:
1. Get an API key from https://www.assemblyai.com/
2. Add to Railway Variables: ASSEMBLYAI_API_KEY=your-key-here
3. Redeploy your application

AssemblyAI Features Available:
✓ High-accuracy speech recognition
✓ Speaker diarization (identify who is speaking)
✓ Auto-generated chapters
✓ Punctuation and formatting
✓ Multiple language support
✓ Faster than real-time transcription

This placeholder text can be used to test question generation.

Sample lecture content:
The complexity of building conversational AI systems depends on several factors. Modern chatbots range from simple rule-based systems to sophisticated AI assistants powered by large language models. Key considerations include natural language understanding, context management, integration capabilities, and user experience design.

When building a chatbot, developers must balance complexity with functionality. Simple FAQ bots can be effective for basic queries, while advanced systems can handle multi-turn conversations, maintain context, and provide personalized responses.

Supported formats: MP3, WAV, M4A, FLAC, OGG, WEBM, MP4
Maximum file size: 2.2GB
Typical transcription time: Faster than real-time
"""
    
    return transcript.strip()


def format_transcript(raw_transcript: str) -> str:
    """
    Clean and format transcription.
    """
    import re
    
    cleaned = raw_transcript.strip()
    
    # Remove excessive spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Ensure proper sentence endings
    if cleaned and not cleaned.endswith(('.', '!', '?')):
        cleaned += '.'
    
    return cleaned