import sqlite3


connection = sqlite3.connect("ethnography_ai.db")

cursor = connection.cursor()



cursor.execute("""
CREATE TABLE IF NOT EXISTS session_details (
    session_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER,
    problem TEXT
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS problem_conversation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    domain TEXT,
    subdomain TEXT,
    questions TEXT,
    answers TEXT,

    FOREIGN KEY (session_id)
    REFERENCES session_details(session_id)
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS session_results (
    session_id TEXT PRIMARY KEY,
    patterns TEXT,
    recommendations TEXT,

    FOREIGN KEY (session_id)
    REFERENCES session_details(session_id)
)
""")


connection.commit()

connection.close()


print("Database and tables created successfully.")