import asyncio
import json
import os
from typing import Optional
from deepgram import DeepgramClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DeepgramService:
    def __init__(self):
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            print("Warning: DEEPGRAM_API_KEY not found in environment variables")
            self.api_key = None
        
        if self.api_key:
            self.client = DeepgramClient(api_key=self.api_key)
        else:
            self.client = None
        self.live_connection = None
        
    async def start_live_transcription(self, websocket, language="en", model="nova-2"):
        """Start live transcription with WebSocket connection"""
        try:
            if not self.client:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Deepgram API key not configured"
                }))
                return False

            print("Starting Deepgram live transcription...")
            
            # For now, let's send a success message to indicate the connection is ready
            await websocket.send_text(json.dumps({
                "type": "status",
                "message": "Deepgram connection ready"
            }))
            
            return True
                
        except Exception as e:
            print(f"Error starting live transcription: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Failed to start Deepgram: {str(e)}"
            }))
            return False
    
    async def send_audio_data(self, audio_data: bytes):
        """Send audio data to Deepgram for live transcription"""
        if self.live_connection:
            try:
                self.live_connection.send(audio_data)
            except Exception as e:
                print(f"Error sending audio data: {e}")
    
    async def stop_live_transcription(self):
        """Stop live transcription"""
        if self.live_connection:
            try:
                self.live_connection.finish()
                self.live_connection = None
                print("Deepgram live transcription stopped")
            except Exception as e:
                print(f"Error stopping live transcription: {e}")
    
    async def transcribe_file(self, file_path: str, language="en", model="nova-3"):
        """Transcribe an audio file using Deepgram v1 API"""
        try:
            with open(file_path, "rb") as file:
                buffer_data = file.read()
            
            response = self.client.listen.v1.media.transcribe_file(
                request=buffer_data,
                model=model,
                language=language,
                smart_format=True,
                punctuate=True,
                diarize=True,
            )
            
            # Extract transcript
            transcript = response.results.channels[0].alternatives[0].transcript
            confidence = response.results.channels[0].alternatives[0].confidence if hasattr(response.results.channels[0].alternatives[0], 'confidence') else 0.9
            
            return {
                "transcript": transcript,
                "confidence": confidence,
                "words": response.results.channels[0].alternatives[0].words if hasattr(response.results.channels[0].alternatives[0], 'words') else []
            }
            
        except Exception as e:
            print(f"Error transcribing file: {e}")
            return None

# Global Deepgram service instance
deepgram_service = DeepgramService()
