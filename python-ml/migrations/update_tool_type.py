from app.utils.db import get_db_connection

def update_tool_type():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE tools SET tool_type = 'GitHub' WHERE id = 46")
        conn.commit()
        print("Successfully updated GitHub tool type")
    except Exception as e:
        print(f"Error updating tool type: {str(e)}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    update_tool_type() 