import sqlite3


class Database:
	GAMES_DB = "dbs/games.db"
	TASKS_DB = "dbs/tasks.db"
	EVENTS_DB = "dbs/events.db"

	@staticmethod
	def add_game(name, repo_name, channel_id, owner):
		Database.insert_into_db(Database.GAMES_DB, "games", name=name, repo_name=repo_name, channel_id=channel_id, owner=owner.name, owner_display_name=owner.display_name)	


	@staticmethod
	def get_game_info(channel_id):
		return Database.fetch_one_as_dict(Database.GAMES_DB, "games", "channel_id = ?", (channel_id,))	


	@staticmethod
	def get_game_channel(game_id):
		game = Database.fetch_one_as_dict(Database.GAMES_DB, "games", "id = ?", (game_id,))
		return game["channel_id"] if game else None
	

	@staticmethod
	def get_default_game_info():
		return Database.fetch_one_as_dict(Database.GAMES_DB, "games", "id = ?", (1,))	


	@staticmethod
	def add_task(user_id, description, deadline=None, event_id=None):
		Database.insert_into_db(Database.TASKS_DB, "tasks", user_id=user_id, description=description, deadline=deadline, event_id=event_id)


	@staticmethod
	def register_contributor(discord_username, credit_name, discord_display_name=None, itch_io_link=None, alt_link=None):
		Database.insert_into_db(Database.GAMES_DB, "contributors", discord_username=discord_username, credit_name=credit_name, discord_display_name=discord_display_name, itch_io_link=itch_io_link, alt_link=alt_link)


	@staticmethod
	def add_asset_request(game_id, asset_type, content, context, requested_by):
		Database.insert_into_db(Database.GAMES_DB, "asset_requests", game_id=game_id, asset_type=asset_type, content=content, context=context, requested_by=requested_by, status="Pending")	


	@staticmethod
	def mark_request_accepted(request_id, user):
		Database.update_field(Database.GAMES_DB, "asset_requests", request_id, "status", "Accepted")
		Database.update_field(Database.GAMES_DB, "asset_requests", request_id, "accepted_by", user)


	@staticmethod
	def mark_request_finished(request_id):
		Database.update_field(Database.GAMES_DB, "asset_requests", request_id, "status", "Finished")


	@staticmethod
	def get_asset_requests_by_type(type, status= "Pending", user= None):
		if user:
			return Database.fetch_all_as_dict_arr(
				Database.GAMES_DB,
				"asset_requests",
				#"asset_type = ? AND status = ? AND substr(requested_by, 1, instr(requested_by, ' ') - 1) = ?",
				"asset_type = ? AND status = ? AND requested_by = ?",
				(type, status, user),
			)
		else:
			return Database.fetch_all_as_dict_arr(Database.GAMES_DB, "asset_requests", f"asset_type = ? AND status = '{status}'", (type,))
	
	
	@staticmethod
	def insert_into_db(db_path, table, **columns) -> bool:
		conn = sqlite3.connect(db_path)
		cursor = conn.cursor()
				
		keys = ', '.join(columns.keys())
		placeholders = ', '.join(['?'] * len(columns))
		values = tuple(columns.values())
		
		try:
			cursor.execute(f"INSERT INTO {table} ({keys}) VALUES ({placeholders})", values)
			conn.commit()
			return True
		except sqlite3.IntegrityError as e:
			# unique constraint or other integrity failure
			print(f"[DB] Insert failed: {e}")
			return False
		finally:
			conn.close()


	@staticmethod
	def update_field(db_path: str, table: str, row_id: int, field: str, value):
		conn = sqlite3.connect(db_path)
		cursor = conn.cursor()

		print("Updating field:", field, "to value:", value, "in table:", table, "for row ID:", row_id)


		# Use parameterized query to avoid SQL injection
		query = f"UPDATE {table} SET {field} = ? WHERE id = ?"
		cursor.execute(query, (value, row_id))

		conn.commit()
		conn.close()


	@staticmethod
	def fetch_one_as_dict(db_path: str, table: str, where: str, params: tuple = ()) -> dict | None:
		conn = sqlite3.connect(db_path)
		cursor = conn.cursor()

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


	@staticmethod
	def fetch_all_as_dict_arr(db_path: str, table: str, where: str = "1=1", params: tuple = ()) -> list[dict]:
		conn = sqlite3.connect(db_path)
		cursor = conn.cursor()

		query = f"SELECT * FROM {table} WHERE {where}"
		print(f"Executing query: {query} with params: {params}")
		cursor.execute(query, params)
		rows = cursor.fetchall()

		if not rows:
			print("No rows found")
			conn.close()
			return []

		col_names = [desc[0] for desc in cursor.description]
		conn.close()

		return [dict(zip(col_names, row)) for row in rows]


	@staticmethod
	def entry_exists(db_path: str, table: str, field: str, value) -> bool:
		return Database.fetch_one_as_dict(db_path, table, f"{field} = ?", (value,)) is not None


	@staticmethod
	def execute(db_path: str, query: str, params: tuple = ()) -> list[tuple]:
		conn = sqlite3.connect(db_path)
		cursor = conn.cursor()
		cursor.execute(query, params)
		rows = cursor.fetchall()
		conn.close()
		return rows



def setup_db(db_name, table_schemas):
	conn = sqlite3.connect(db_name)
	cursor = conn.cursor()
	for schema in table_schemas:
		cursor.execute(f"CREATE TABLE IF NOT EXISTS {schema['name']} ({schema['columns']})")
	conn.commit()
	conn.close()


setup_db(Database.GAMES_DB, [{"name": "games", "columns": "id INTEGER PRIMARY KEY, name TEXT, repo_name TEXT, channel_id INTEGER, owner TEXT, itch_io_link TEXT"}])
setup_db(Database.TASKS_DB, [{"name": "tasks", "columns": "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, description TEXT NOT NULL, deadline TEXT, finished INTEGER DEFAULT 0, event_id INTEGER DEFAULT NULL"}])
setup_db(Database.EVENTS_DB, [{"name": "events", "columns": "id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, triggered INTEGER DEFAULT 0"}])
setup_db(Database.GAMES_DB, [{"name": "contributors", "columns": "id INTEGER PRIMARY KEY AUTOINCREMENT, discord_username TEXT NOT NULL, discord_display_name TEXT, credit_name TEXT NOT NULL, itch_io_link TEXT, alt_link TEXT"}])
setup_db(Database.GAMES_DB, [{"name": "game_contributors", "columns": "game_id INTEGER NOT NULL, contributor_id INTEGER NOT NULL, role TEXT NOT NULL, PRIMARY KEY (game_id, contributor_id, role), FOREIGN KEY (game_id) REFERENCES games(id), FOREIGN KEY (contributor_id) REFERENCES contributors(id)"}])
setup_db(Database.GAMES_DB, [{"name": "asset_requests", "columns": "id INTEGER PRIMARY KEY AUTOINCREMENT, game_id INTEGER NOT NULL, asset_type TEXT NOT NULL, content TEXT NOT NULL, context TEXT, requested_by INTEGER NOT NULL, accepted_by INTEGER, status TEXT NOT NULL, FOREIGN KEY (game_id) REFERENCES games(id), FOREIGN KEY (requested_by) REFERENCES contributors(id), FOREIGN KEY (accepted_by) REFERENCES contributors(id)"}])
