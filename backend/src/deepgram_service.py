import asyncio
import json
import os
from typing import Optional
from deepgram import DeepgramClient
from deepgram.core.events import EventType
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DeepgramService:
    def __init__(self):
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY not found in environment variables")
        
        self.client = DeepgramClient(api_key=self.api_key)
        self.live_connection = None
        
    async def start_live_transcription(self, websocket, language="en", model="flux-general-en"):
        """Start live transcription with WebSocket connection using v2 API"""
        try:
            # Create live transcription connection using v2 API
            # Note: v2 API uses model names that include language (e.g., flux-general-en)
            self.live_connection = self.client.listen.v2.connect(
                model=model,
                smart_format=True,
                interim_results=True,
                utterance_end_ms=1000,
                vad_events=True,
                encoding="linear16",
                channels=1,
                sample_rate=16000,
            )
            
            # Set up event handlers
            def on_open(event):
                print("Deepgram connection opened")
            
            def on_message(message):
                try:
                    if hasattr(message, 'channel') and hasattr(message.channel, 'alternatives'):
                        transcript = message.channel.alternatives[0].transcript
                        if transcript:
                            # Send transcription back to frontend
                            asyncio.create_task(
                                websocket.send_text(json.dumps({
                                    "type": "transcription",
                                    "text": transcript,
                                    "is_final": message.is_final if hasattr(message, 'is_final') else True
                                }))
                            )
                except Exception as e:
                    print(f"Error processing message: {e}")
            
            def on_error(error):
                print(f"Deepgram error: {error}")
                asyncio.create_task(
                    websocket.send_text(json.dumps({
                        "type": "error",
                        "message": str(error)
                    }))
                )
            
            def on_close(event):
                print("Deepgram connection closed")
            
            # Register event handlers
            self.live_connection.on(EventType.OPEN, on_open)
            self.live_connection.on(EventType.MESSAGE, on_message)
            self.live_connection.on(EventType.ERROR, on_error)
            self.live_connection.on(EventType.CLOSE, on_close)
            
            # Start listening
            self.live_connection.start_listening()
            print("Deepgram live transcription started")
            return True
                
        except Exception as e:
            print(f"Error starting live transcription: {e}")
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
