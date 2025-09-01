import sqlite3

GAMES_DB = "dbs/games.db"


def add_game(name, repo_name, channel_id, owner):
	conn = sqlite3.connect(GAMES_DB)
	cursor = conn.cursor()
	cursor.execute(
		"INSERT INTO games (name, repo_name, channel_id, owner) VALUES (?, ?, ?, ?)",
		(name, repo_name, channel_id, owner),
	)
	conn.commit()
	conn.close()


def setup_db(db_name, table_schemas):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    for schema in table_schemas:
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {schema['name']} ({schema['columns']})")
    conn.commit()
    conn.close()


setup_db(GAMES_DB, [{"name": "games", "columns": "id INTEGER PRIMARY KEY, name TEXT, repo_name TEXT, channel_id INTEGER, owner TEXT"}])
