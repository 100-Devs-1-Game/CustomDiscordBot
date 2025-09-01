import sqlite3

GAMES_DB = "dbs/games.db"
TASKS_DB = "dbs/tasks.db"
EVENTS_DB = "dbs/events.db"


class Database:
	@staticmethod
	def add_game(name, repo_name, channel_id, owner):
		Database.insert_into_db(GAMES_DB, "games", name=name, repo_name=repo_name, channel_id=channel_id, owner=owner)	


	@staticmethod
	def add_task(user_id, description, deadline=None, event_id=None):
		Database.insert_into_db(TASKS_DB, "tasks", user_id=user_id, description=description, deadline=deadline, event_id=event_id)


	@staticmethod
	def insert_into_db(db_path, table, **columns):
		conn = sqlite3.connect(db_path)
		cursor = conn.cursor()
		
		keys = ', '.join(columns.keys())
		placeholders = ', '.join(['?'] * len(columns))
		values = tuple(columns.values())
		
		cursor.execute(f"INSERT INTO {table} ({keys}) VALUES ({placeholders})", values)
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
setup_db(TASKS_DB, [{"name": "tasks", "columns": "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, description TEXT NOT NULL, deadline TEXT, finished INTEGER DEFAULT 0, event_id INTEGER DEFAULT NULL"}])
setup_db(EVENTS_DB, [{"name": "events", "columns": "Id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, triggered INTEGER DEFAULT 0"}])