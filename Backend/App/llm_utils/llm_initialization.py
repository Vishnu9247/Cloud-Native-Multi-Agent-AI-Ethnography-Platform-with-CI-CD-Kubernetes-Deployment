from App.llm_utils.llm_client import invoke_llm


def get_response(prompt):
    return invoke_llm(prompt, purpose="legacy.get_response")
