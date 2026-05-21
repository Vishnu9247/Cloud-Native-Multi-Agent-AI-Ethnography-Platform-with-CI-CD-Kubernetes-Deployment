from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.post('/record')
def audio_to_text():
    try:
        from App.audio_utils.audio_service_one import record_and_transcribe
    except ImportError as error:
        raise HTTPException(
            status_code=503,
            detail="Audio transcription dependencies are not installed in this deployment.",
        ) from error

    text = record_and_transcribe()
    
    return {
        'transcription': text
    }

