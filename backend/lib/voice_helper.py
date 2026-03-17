import os
import io
from google.cloud import speech, texttospeech
from dotenv import load_dotenv

load_dotenv()

class VoiceHelper:
    def __init__(self):
        self.project_id = os.getenv("PROJECT_ID")
        self._speech_client = None
        self._tts_client = None

    @property
    def speech_client(self):
        if self._speech_client is None:
            self._speech_client = speech.SpeechClient()
        return self._speech_client

    @property
    def tts_client(self):
        if self._tts_client is None:
            self._tts_client = texttospeech.TextToSpeechClient()
        return self._tts_client

    def transcribe_stream(self, audio_generator):
        """
        Transcribes a stream of audio bytes using Google Cloud STT.
        """
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
        )
        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True
        )

        requests = (speech.StreamingRecognizeRequest(audio_content=content) for content in audio_generator)
        
        responses = self.speech_client.streaming_recognize(streaming_config, requests)
        return responses

    def synthesize_speech(self, text: str) -> bytes:
        """
        Synthesizes text into speech bytes using Google Cloud TTS.
        """
        input_text = texttospeech.SynthesisInput(text=text)
        
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Neural2-F",
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = self.tts_client.synthesize_speech(
            input=input_text,
            voice=voice,
            audio_config=audio_config
        )
        
        return response.audio_content

voice_helper = VoiceHelper()
