import sqlite3
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from config import DB_NAME


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            gender TEXT,
            weight REAL,
            height REAL,
            age REAL,
            activity_level REAL,
            water_goal REAL,
            calorie_goal REAL,
            goal_type TEXT DEFAULT 'maintain',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    try:
        cur.execute("ALTER TABLE users ADD COLUMN goal_type TEXT DEFAULT 'maintain'")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS food_entries(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            description TEXT,
            calories REAL,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS water_entries(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    conn.commit()
    conn.close()


def save_user_to_db(user_id: int, user_data: dict):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, gender, weight, height, age, activity_level, water_goal, calorie_goal, goal_type) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            user_data.get("gender"),
            user_data.get("weight"),
            user_data.get("height"),
            user_data.get("age"),
            user_data.get("activity_level"),
            user_data.get("water_goal"),
            user_data.get("calorie_goal"),
            user_data.get("goal_type", "maintain")
        ))
        conn.commit()
    except Exception as e:
        print(f"Ошибка сохранения пользователя в БД: {e}")
        conn.rollback()
    finally:
        conn.close()


def get_user_profile(user_id: int) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT gender, weight, height, age, activity_level, water_goal, calorie_goal, goal_type
        FROM users WHERE user_id = ?
    ''', (user_id,))
    result = cur.fetchone()
    conn.close()

    if result:
        return {
            'gender': result[0],
            'weight': result[1],
            'height': result[2],
            'age': result[3],
            'activity_level': result[4],
            'water_goal': result[5],
            'calorie_goal': result[6],
            'goal_type': result[7] if result[7] else 'maintain'
        }
    return None


def update_user_field(user_id: int, field: str, value):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if not cur.fetchone():
            print(f'Пользователь {user_id} не найден')
            return False

        cur.execute(f'UPDATE users SET {field} = ? WHERE user_id = ?', (value, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f'Ошибка обновления поля {field}: {e}')
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_user_profile(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if not cur.fetchone():
            return False

        cur.execute('DELETE FROM food_entries WHERE user_id = ?', (user_id,))
        cur.execute('DELETE FROM water_entries WHERE user_id = ?', (user_id,))
        cur.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f'Ошибка удаления профиля: {e}')
        conn.rollback()
        return False
    finally:
        conn.close()


def add_food_entry(user_id: int, description: str, calories: float, entry_date: Optional[date] = None):
    if entry_date is None:
        entry_date = date.today()
    
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT INTO food_entries (user_id, description, calories, date)
            VALUES (?, ?, ?, ?)
        ''', (user_id, description, calories, entry_date))
        conn.commit()
        return True
    except Exception as e:
        print(f'Ошибка добавления записи еды: {e}')
        conn.rollback()
        return False
    finally:
        conn.close()


def add_water_entry(user_id: int, amount: float, entry_date: Optional[date] = None):
    if entry_date is None:
        entry_date = date.today()
    
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT INTO water_entries (user_id, amount, date)
            VALUES (?, ?, ?)
        ''', (user_id, amount, entry_date))
        conn.commit()
        return True
    except Exception as e:
        print(f'Ошибка добавления записи воды: {e}')
        conn.rollback()
        return False
    finally:
        conn.close()


def get_daily_calories(user_id: int, entry_date: Optional[date] = None) -> float:
    if entry_date is None:
        entry_date = date.today()
    
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT COALESCE(SUM(calories), 0) FROM food_entries
        WHERE user_id = ? AND date = ?
    ''', (user_id, entry_date))
    result = cur.fetchone()[0] or 0.0
    conn.close()
    return float(result)


def get_daily_water(user_id: int, entry_date: Optional[date] = None) -> float:
    if entry_date is None:
        entry_date = date.today()
    
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT COALESCE(SUM(amount), 0) FROM water_entries
        WHERE user_id = ? AND date = ?
    ''', (user_id, entry_date))
    result = cur.fetchone()[0] or 0.0
    conn.close()
    return float(result)


def get_monthly_stats(user_id: int, year: int, month: int) -> Dict[str, List]:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute('''
        SELECT date, COALESCE(SUM(calories), 0) as total_calories
        FROM food_entries
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        GROUP BY date
        ORDER BY date
    ''', (user_id, str(year), f"{month:02d}"))
    calories_data = cur.fetchall()

    cur.execute('''
        SELECT date, COALESCE(SUM(amount), 0) as total_water
        FROM water_entries
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        GROUP BY date
        ORDER BY date
    ''', (user_id, str(year), f"{month:02d}"))
    water_data = cur.fetchall()
    
    conn.close()

    calories_dict = {}
    for row in calories_data:
        date_val = row[0]
        if isinstance(date_val, str):
            date_key = date_val
        else:
            date_key = date_val.strftime('%Y-%m-%d') if hasattr(date_val, 'strftime') else str(date_val)
        calories_dict[date_key] = row[1]
    
    water_dict = {}
    for row in water_data:
        date_val = row[0]
        if isinstance(date_val, str):
            date_key = date_val
        else:
            date_key = date_val.strftime('%Y-%m-%d') if hasattr(date_val, 'strftime') else str(date_val)
        water_dict[date_key] = row[1]

    all_dates = sorted(set(list(calories_dict.keys()) + list(water_dict.keys())))
    
    calories_list = [calories_dict.get(d, 0.0) for d in all_dates]
    water_list = [water_dict.get(d, 0.0) for d in all_dates]
    
    return {
        'dates': all_dates,
        'calories': calories_list,
        'water': water_list
    }
