import psycopg2
from datetime import datetime

# --- Database Connection Configuration ---
# You need to replace these with your actual PostgreSQL database credentials.
# It is recommended to use environment variables in a production environment.
DB_HOST = "localhost"
DB_NAME = "pms"
DB_USER = "postgres"
DB_PASS = "postgrespv"

def get_db_connection():
    """Establishes and returns a new database connection."""
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
    except psycopg2.OperationalError as e:
        print(f"Error connecting to database: {e}")
    return conn

def create_tables():
    """
    Creates the necessary database tables if they don't already exist.
    This function should be run once to initialize the database schema.
    """
    conn = get_db_connection()
    if conn is None:
        return
    
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL
            );

            CREATE TABLE IF NOT EXISTS goals (
                id SERIAL PRIMARY KEY,
                employee_id INTEGER REFERENCES employees(id) ON DELETE CASCADE,
                description TEXT NOT NULL,
                due_date DATE,
                status VARCHAR(50) NOT NULL DEFAULT 'Draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                goal_id INTEGER REFERENCES goals(id) ON DELETE CASCADE,
                employee_id INTEGER REFERENCES employees(id) ON DELETE CASCADE,
                description TEXT NOT NULL,
                is_approved BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY,
                goal_id INTEGER REFERENCES goals(id) ON DELETE CASCADE,
                manager_id INTEGER REFERENCES employees(id) ON DELETE CASCADE,
                feedback_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Error creating tables: {e}")
    finally:
        cur.close()
        conn.close()

# --- Manager and Employee Management ---
def get_all_employees():
    """Reads and returns a list of all employees."""
    conn = get_db_connection()
    if conn is None:
        return []
    
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, name FROM employees ORDER BY name;")
        employees = cur.fetchall()
        return employees
    except psycopg2.Error as e:
        print(f"Error fetching employees: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def add_employee(name):
    """Creates a new employee."""
    conn = get_db_connection()
    if conn is None:
        return
    
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO employees (name) VALUES (%s) RETURNING id;", (name,))
        employee_id = cur.fetchone()[0]
        conn.commit()
        return employee_id
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Error adding employee: {e}")
        return None
    finally:
        cur.close()
        conn.close()

# --- CRUD for Goals ---
def create_goal(employee_id, description, due_date, status="Draft"):
    """Creates a new goal for an employee."""
    conn = get_db_connection()
    if conn is None:
        return False
    
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO goals (employee_id, description, due_date, status) VALUES (%s, %s, %s, %s);",
            (employee_id, description, due_date, status)
        )
        conn.commit()
        return True
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Error creating goal: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def read_goals(employee_id=None):
    """Reads and returns goals. Can be filtered by employee_id."""
    conn = get_db_connection()
    if conn is None:
        return []
    
    cur = conn.cursor()
    try:
        if employee_id:
            cur.execute("SELECT g.id, e.name, g.description, g.due_date, g.status FROM goals g JOIN employees e ON g.employee_id = e.id WHERE g.employee_id = %s ORDER BY g.due_date DESC;", (employee_id,))
        else:
            cur.execute("SELECT g.id, e.name, g.description, g.due_date, g.status FROM goals g JOIN employees e ON g.employee_id = e.id ORDER BY g.due_date DESC;")
        goals = cur.fetchall()
        return goals
    except psycopg2.Error as e:
        print(f"Error reading goals: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def update_goal_status(goal_id, status):
    """Updates the status of a specific goal."""
    conn = get_db_connection()
    if conn is None:
        return False
    
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE goals SET status = %s WHERE id = %s;",
            (status, goal_id)
        )
        conn.commit()
        return cur.rowcount > 0
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Error updating goal status: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def delete_goal(goal_id):
    """Deletes a goal and its associated tasks and feedback."""
    conn = get_db_connection()
    if conn is None:
        return False
    
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM goals WHERE id = %s;", (goal_id,))
        conn.commit()
        return cur.rowcount > 0
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Error deleting goal: {e}")
        return False
    finally:
        cur.close()
        conn.close()

# --- CRUD for Tasks ---
def create_task(goal_id, employee_id, description):
    """Creates a new task for a goal."""
    conn = get_db_connection()
    if conn is None:
        return False
    
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO tasks (goal_id, employee_id, description) VALUES (%s, %s, %s);",
            (goal_id, employee_id, description)
        )
        conn.commit()
        return True
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Error creating task: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def read_tasks(goal_id=None, employee_id=None):
    """Reads and returns tasks, can be filtered by goal or employee."""
    conn = get_db_connection()
    if conn is None:
        return []
    
    cur = conn.cursor()
    try:
        if goal_id:
            cur.execute("SELECT id, description, is_approved FROM tasks WHERE goal_id = %s ORDER BY created_at DESC;", (goal_id,))
        elif employee_id:
            cur.execute("SELECT t.id, g.description, t.description, t.is_approved FROM tasks t JOIN goals g ON t.goal_id = g.id WHERE t.employee_id = %s ORDER BY t.created_at DESC;", (employee_id,))
        else:
            cur.execute("SELECT id, description, is_approved FROM tasks ORDER BY created_at DESC;")
        tasks = cur.fetchall()
        return tasks
    except psycopg2.Error as e:
        print(f"Error reading tasks: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def update_task_approval(task_id, is_approved):
    """Updates the approval status of a task."""
    conn = get_db_connection()
    if conn is None:
        return False
    
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE tasks SET is_approved = %s WHERE id = %s;",
            (is_approved, task_id)
        )
        conn.commit()
        return cur.rowcount > 0
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Error updating task approval: {e}")
        return False
    finally:
        cur.close()
        conn.close()

# --- CRUD for Feedback ---
def create_feedback(goal_id, manager_id, feedback_text):
    """Creates new feedback for a goal."""
    conn = get_db_connection()
    if conn is None:
        return False
    
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO feedback (goal_id, manager_id, feedback_text) VALUES (%s, %s, %s);",
            (goal_id, manager_id, feedback_text)
        )
        conn.commit()
        return True
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Error creating feedback: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def read_feedback(goal_id=None):
    """Reads feedback, filtered by goal_id."""
    conn = get_db_connection()
    if conn is None:
        return []
    
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, feedback_text, created_at FROM feedback WHERE goal_id = %s ORDER BY created_at DESC;",
            (goal_id,)
        )
        feedback = cur.fetchall()
        return feedback
    except psycopg2.Error as e:
        print(f"Error reading feedback: {e}")
        return []
    finally:
        cur.close()
        conn.close()

# --- Reporting and Business Insights ---
def get_performance_history(employee_id):
    """Retrieves all goals and associated feedback for an employee."""
    conn = get_db_connection()
    if conn is None:
        return [], []
    
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, description, due_date, status, created_at FROM goals WHERE employee_id = %s ORDER BY created_at DESC;",
            (employee_id,)
        )
        goals = cur.fetchall()
        
        history = []
        for goal_id, description, due_date, status, created_at in goals:
            cur.execute(
                "SELECT feedback_text, created_at FROM feedback WHERE goal_id = %s ORDER BY created_at DESC;",
                (goal_id,)
            )
            feedbacks = cur.fetchall()
            history.append({
                'goal_id': goal_id,
                'description': description,
                'due_date': due_date,
                'status': status,
                'created_at': created_at,
                'feedbacks': feedbacks
            })
        return history
    except psycopg2.Error as e:
        print(f"Error fetching performance history: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def get_goal_status_counts(employee_id=None):
    """Returns a count of goals by status."""
    conn = get_db_connection()
    if conn is None:
        return {}
    
    cur = conn.cursor()
    try:
        if employee_id:
            cur.execute("SELECT status, COUNT(*) FROM goals WHERE employee_id = %s GROUP BY status;", (employee_id,))
        else:
            cur.execute("SELECT status, COUNT(*) FROM goals GROUP BY status;")
        counts = dict(cur.fetchall())
        return counts
    except psycopg2.Error as e:
        print(f"Error fetching status counts: {e}")
        return {}
    finally:
        cur.close()
        conn.close()

def get_avg_days_to_complete_goal(employee_id=None):
    """Returns the average number of days to complete a goal."""
    conn = get_db_connection()
    if conn is None:
        return None
    
    cur = conn.cursor()
    try:
        if employee_id:
            cur.execute("SELECT AVG(EXTRACT(EPOCH FROM (due_date - created_at))) / 86400 FROM goals WHERE employee_id = %s AND status = 'Completed';", (employee_id,))
        else:
            cur.execute("SELECT AVG(EXTRACT(EPOCH FROM (due_date - created_at))) / 86400 FROM goals WHERE status = 'Completed';")
        avg_days = cur.fetchone()[0]
        return avg_days
    except psycopg2.Error as e:
        print(f"Error fetching average completion time: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def get_max_min_due_date():
    """Returns the earliest and latest goal due dates."""
    conn = get_db_connection()
    if conn is None:
        return None, None
    
    cur = conn.cursor()
    try:
        cur.execute("SELECT MIN(due_date), MAX(due_date) FROM goals;")
        min_date, max_date = cur.fetchone()
        return min_date, max_date
    except psycopg2.Error as e:
        print(f"Error fetching min/max dates: {e}")
        return None, None
    finally:
        cur.close()
        conn.close()

def get_total_tasks_approved():
    """Returns the total number of approved tasks."""
    conn = get_db_connection()
    if conn is None:
        return 0
    
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM tasks WHERE is_approved = TRUE;")
        count = cur.fetchone()[0]
        return count
    except psycopg2.Error as e:
        print(f"Error fetching total approved tasks: {e}")
        return 0
    finally:
        cur.close()
        conn.close()