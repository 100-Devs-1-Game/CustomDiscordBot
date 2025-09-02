import sqlite3

GAMES_DB = "dbs/games.db"
TASKS_DB = "dbs/tasks.db"
EVENTS_DB = "dbs/events.db"


class Database:
	@staticmethod
	def add_game(name, repo_name, channel_id, owner):
		Database.insert_into_db(GAMES_DB, "games", name=name, repo_name=repo_name, channel_id=channel_id, owner=owner)	


	@staticmethod
	def get_game_info(channel_id):
		return Database.fetch_one_as_dict(GAMES_DB, "games", "channel_id = ?", (channel_id,))	


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


	@staticmethod
	def fetch_one_as_dict(db_path: str, table: str, where: str, params: tuple = ()) -> dict | None:
		conn = sqlite3.connect(db_path)
		cursor = conn.cursor()

		cursor.execute("PRAGMA database_list;")
		print("database_list:", cursor.fetchall())

		cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table';")
		print("tables:", cursor.fetchall())

		cursor.execute(f"SELECT COUNT(*) FROM {table};")
		print("Row count:", cursor.fetchone()[0])

		query = f"SELECT * FROM {table} WHERE {where} LIMIT 1"
		print(f"Executing query: {query} with params: {params}")
		cursor.execute(query, params)
		row = cursor.fetchone()
		if not row:
			print("No row found")
			conn.close()
			return None

		col_names = [desc[0] for desc in cursor.description]
		conn.close()

		return dict(zip(col_names, row))



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