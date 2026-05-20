import sqlite3
from typing import List, Dict
from typing_extensions import TypedDict




DATABASE_NAME = "ethnography_ai.db"

session_json = {
    "session_id": "session_001",
    "name": "Vishnu",
    "age": 24,
    "problem": "I am struggling to apply for jobs after graduation."
}


conversation_json = {
    "session_id": "session_001",
    "domain": "Aspirational",
    "subdomain": "Career Goals",
    "questions": "What makes it difficult for you to start applying for jobs?",
    "answers": "I keep thinking I need to learn more technologies before applying."
}


def insert_session_details(data):
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()

    cursor.execute("""
    INSERT OR REPLACE INTO session_details (
        session_id,
        name,
        age,
        problem
    )
    VALUES (?, ?, ?, ?)
    """, (
        data["session_id"],
        data["name"],
        data["age"],
        data.get("problem")
    ))

    connection.commit()
    connection.close()




def insert_problem_conversation(data):
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()

    cursor.execute("""
    INSERT INTO problem_conversation (
        session_id,
        domain,
        subdomain,
        questions,
        answers
    )
    VALUES (?, ?, ?, ?, ?)
    """, (
        data["session_id"],
        data.get("domain"),
        data.get("subdomain"),
        data.get("questions"),
        data.get("answers")
    ))

    connection.commit()
    connection.close()


def insert_session_results(data):
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()

    cursor.execute("""
    INSERT INTO session_results (
        session_id,
        patterns,
        recommendations           
    )
    VALUES (?, ?, ?)
    """, (
        data['session_id'],
        data.get('patterns'),
        data.get('recommendations')
    ))

    connection.commit()
    connection.close()
