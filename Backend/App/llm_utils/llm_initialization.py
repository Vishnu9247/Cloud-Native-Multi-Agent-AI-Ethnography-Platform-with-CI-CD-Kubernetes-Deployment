import requests

model_name = 'llama3.2'

url = "http://localhost:11434/api/generate"

def get_response(prompt):
    payload = {
        "model": 'llama3.2',
        "prompt": prompt,
        "stream" : False
        }
    result = requests.post(url,json = payload).json()
    response = result['response']
    return response.strip()