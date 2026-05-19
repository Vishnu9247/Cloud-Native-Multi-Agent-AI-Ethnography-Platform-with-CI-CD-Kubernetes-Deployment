from fastapi import FastAPI

from App.api.routes.vector_store import router as vector_router
from App.api.routes.audio import router as audio_router
from App.api.routes.agent_one import router as problem_framing_router
from App.api.routes.agent_two import router as domain_selection_router
from App.api.routes.agent_three import router as interview_router
from App.api.routes.agent_four import router as identify_patterns


app = FastAPI()

app.include_router(vector_router, prefix = '/vector', tags = ['Vector Store'])
app.include_router(audio_router, prefix = '/audio', tags = ['Audio'])
app.include_router(problem_framing_router, prefix = '/agent', tags = ['Problem Framing Agent'])
app.include_router(domain_selection_router, prefix = '/agent', tags = ['Domain Selection Agent'])
app.include_router(interview_router, prefix= '/agent', tags= ['Interview Agent'])
app.include_router(identify_patterns, prefix='/agent', tags = ['Pattern Identification'])
