from fastapi import UploadFile
import os
from typing import Optional

# Try to import AssemblyAI
try:
    import assemblyai as aai
    ASSEMBLYAI_AVAILABLE = True
except ImportError:
    ASSEMBLYAI_AVAILABLE = False
    print("⚠️ AssemblyAI not installed. Run: pip install assemblyai")


async def transcribe_audio(file: UploadFile) -> str:
    """
    Transcribe audio file to text using AssemblyAI.
    """
    # Read file content
    content = await file.read()
    filename = file.filename or "audio_file"
    file_size = len(content)
    
    # Check for AssemblyAI API key and library
    api_key = os.environ.get("ASSEMBLYAI_API_KEY")
    
    if not ASSEMBLYAI_AVAILABLE:
        print("⚠️ AssemblyAI library not installed")
        return generate_placeholder_transcript(filename, file_size)
    
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
    if not ASSEMBLYAI_AVAILABLE:
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


def generate_placeholder_transcript(filename: str, file_size: int) -> str:
    """
    Generate placeholder when API key not available.
    """
    transcript = f"""This is a placeholder transcription for: {filename}

File size: {file_size / 1024:.1f} KB

To enable real AssemblyAI transcription:
1. Install: pip install assemblyai
2. Get API key from https://www.assemblyai.com/
3. Add to Railway: ASSEMBLYAI_API_KEY=your-key-here
4. Redeploy your application

This placeholder allows you to test the system without transcription.

Sample lecture content about conversational AI:

The complexity of building conversational AI systems depends on several factors. Modern chatbots range from simple rule-based systems to sophisticated AI assistants powered by large language models.

Key considerations include:
1. Natural Language Understanding (NLU)
2. Context management across conversations
3. Integration with existing systems
4. User experience design
5. Scalability and performance

Simple FAQ bots work well for basic queries, while advanced systems can handle multi-turn conversations, maintain context across sessions, and provide highly personalized responses based on user history and preferences.

When architecting a chatbot solution, teams must balance complexity with functionality. Over-engineering can lead to maintenance challenges, while under-engineering may result in poor user experiences.

Best practices include:
- Start simple and iterate based on user feedback
- Implement proper error handling and fallback mechanisms
- Monitor conversations to identify improvement opportunities
- Maintain a clear escalation path to human agents when needed
- Regularly update the knowledge base with new information

The future of conversational AI involves more sophisticated natural language processing, better context retention, emotional intelligence, and seamless integration across multiple channels and platforms.
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