from fastapi import APIRouter
from App.audio_utils.audio_service_one import record_and_transcribe

router = APIRouter()

@router.post('/record')
def audio_to_text():
    text = record_and_transcribe()
    
    return {
        'transcription': text
    }

