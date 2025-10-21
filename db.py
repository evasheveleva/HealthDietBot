import sqlite3

def init_db():
    conn = sqlite3.connect('tg.db')
    cur = conn.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS users("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "user_id INTEGER UNIQUE NOT NULL,"
                "weight INTEGER,"
                "height INTEGER,"
                "age INTEGER,"
                "activity_lvl INTEGER,"
                "water_goal FLOAT,"
                "calorie_goal FLOAT)")
    conn.commit()
    conn.close()

def save_user_to_db(user_id: int, user_data: dict):
    conn = sqlite3.connect('tg.db')
    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, weight, height, age, activity_lvl, water_goal, calorie_goal) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
            user_id,
            user_data.get("weight"),
            user_data.get("height"),
            user_data.get("age"),
            user_data.get("activity_lvl"),
            user_data.get("water_goal"),
            user_data.get("calorie_goal")
            ))

        conn.commit()

    except Exception as e:
        print(f"Ошибка сохранения в БД: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_user_from_db(user_id: int) -> dict:
    conn = sqlite3.connect('tg.db')
    cur = conn.cursor()
    cur.execute('''SELECT weight, height, age, activity_lvl, water_goal, calorie_goal
                 FROM users WHERE user_id = ?
                 ''', (user_id,))

    result = cur.fetchone()
    conn.close()

    if result:
        return {
            'weight' : result[0],
            'height' : result[1],
            'age' : result[2],
            'activity_lvl' : result[3],
            'water_goal' : result[4],
            'calorie_goal' : result[5]
        }
    return {}

def update_user_field(user_id: int, field: str, value):
    conn = sqlite3.connect('tg.db')
    cur = conn.cursor()
    try:
        cur.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if not cur.fetchone():
            print(f'Пользователь {user_id} не найден')
            return False

        cur.execute(f'UPDATE users SET {field} = ? WHERE user_id = ?', (value, user_id))
        conn.commit()
        print(f'Поле {field} изменено')
        return True
    except Exception as e:
        print(f'Ошибка обновления поля {field}: {e}')
        conn.rollback()
        return False

    finally:
        conn.close()

def get_user_profile(user_id: int):
    conn = sqlite3.connect('tg.db')
    cur = conn.cursor()

    cur.execute('''
    SELECT weight, height, age, activity_lvl, water_goal, calorie_goal
    FROM users WHERE user_id = ?
    ''', (user_id,))

    result = cur.fetchone()
    conn.close()

    if result:
        return {
            'weight' : result[0],
            'height' : result[1],
            'age' : result[2],
            'activity_lvl' : result[3],
            'water_goal' : result[4],
            'calorie_goal' : result[5]
        }
    return None

def delete_user_profile(user_id: int):
    conn = sqlite3.connect('tg.db')
    cur = conn.cursor()
    try:
        cur.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if not cur.fetchone():
            print(f'Пользователь {user_id} не найден')
            return False
        cur.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f'Ошибка удаления: {e}')
        conn.rollback()
        return False
    finally:
        conn.close()









