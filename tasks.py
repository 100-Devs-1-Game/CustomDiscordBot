import discord
from discord import app_commands
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# DB_NAME = "tasks.db"


# --- Modals ---
class AssignTaskModal(discord.ui.Modal, title="Assign Task"):
    def __init__(self, default_user_id: str):
        super().__init__()
        self.user_id_input = discord.ui.TextInput(
            label="User ID",
            default=default_user_id,
            placeholder="Mention user or enter ID",
            required=True,
        )
        self.description_input = discord.ui.TextInput(
            label="Task Description", placeholder="Describe the task", required=True
        )
        self.deadline_input = discord.ui.TextInput(
            label="Deadline (YYYY-MM-DD)", placeholder="Optional", required=False
        )
        self.add_item(self.user_id_input)
        self.add_item(self.description_input)
        self.add_item(self.deadline_input)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = self.user_id_input.value.strip("<@!>")
        description = self.description_input.value
        deadline = self.deadline_input.value if self.deadline_input.value else None

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (user_id, description, deadline) VALUES (?, ?, ?)",
            (user_id, description, deadline),
        )
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            f"Task assigned to <@{user_id}>!", ephemeral=True
        )


# --- Buttons ---
class TaskButtons(discord.ui.View):
    def __init__(self, task_id):
        super().__init__()
        self.task_id = task_id

    @discord.ui.button(label="Mark Finished", style=discord.ButtonStyle.green)
    async def mark_finished(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET finished=1 WHERE id=?", (self.task_id,))
        conn.commit()
        conn.close()
        await interaction.response.edit_message(
            content="Task marked as finished ✅", view=None
        )


# --- Commands ---
@bot.tree.command(name="assigntask", description="Assign a new task")
async def assigntask(interaction: discord.Interaction):
    # Role check for assigning others
    default_user_id = str(interaction.user.id)
    if "TaskManager" in [role.name for role in interaction.user.roles]:
        modal = AssignTaskModal(default_user_id)
        await interaction.response.send_modal(modal)
    else:
        # If not TaskManager, only allow assigning to self
        modal = AssignTaskModal(default_user_id)
        await interaction.response.send_modal(modal)


@bot.tree.command(name="showtasks", description="Show your tasks")
async def showtasks(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, description, deadline, finished FROM tasks 
        WHERE user_id=? AND (event_id IS NULL OR event_id IN 
            (SELECT id FROM events WHERE triggered=1))
        ORDER BY deadline ASC
    """,
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await interaction.response.send_message(
            "No tasks assigned to you.", ephemeral=True
        )
        return

    for row in rows:
        task_id, desc, deadline, finished = row
        status = "✅ Finished" if finished else "❌ Pending"
        embed = discord.Embed(
            title=f"Task #{task_id}",
            description=f"{desc}\nDeadline: {deadline or 'None'}\nStatus: {status}",
        )
        view = None if finished else TaskButtons(task_id)
        await interaction.user.send(embed=embed, view=view)
    await interaction.response.send_message("Tasks sent to your DMs.", ephemeral=True)


# --- Event Commands ---
@bot.tree.command(name="create_event", description="Create an event")
@app_commands.describe(name="Name of the event")
async def create_event(interaction: discord.Interaction, name: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO events (name) VALUES (?)", (name,))
    event_id = cursor.lastrowid
    conn.commit()
    conn.close()
    await interaction.response.send_message(
        f'Event "{name}" created as #{event_id}', ephemeral=True
    )


@bot.tree.command(name="create_event_task", description="Create task for an event")
@app_commands.describe(event_id="Event ID", description="Task description")
async def create_event_task(
    interaction: discord.Interaction, event_id: int, description: str
):
    user_id = str(interaction.user.id)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (user_id, description, event_id) VALUES (?, ?, ?)",
        (user_id, description, event_id),
    )
    conn.commit()
    conn.close()
    await interaction.response.send_message(
        f"Task for event #{event_id} created.", ephemeral=True
    )


@bot.tree.command(name="trigger_event", description="Trigger an event")
@app_commands.describe(event_id="Event ID")
async def trigger_event(interaction: discord.Interaction, event_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE events SET triggered=1 WHERE id=?", (event_id,))
    conn.commit()
    conn.close()
    await interaction.response.send_message(
        f"Event #{event_id} triggered!", ephemeral=True
    )


# --- Run Bot ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()


bot.run("YOUR_BOT_TOKEN")
