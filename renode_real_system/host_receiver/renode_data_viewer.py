import sqlite3
import pandas as pd
from datetime import datetime

class RenodeDataViewer:
    def __init__(self):
        self.db_path = "renode_sensor_data.db"

    def show_all_data(self):
        """Показывает все данные из базы"""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query("SELECT * FROM renode_sensor_data", conn)
            
            print("📊 ДАННЫЕ ОТ RENODE STM32:")
            print("=" * 80)
            
            if len(df) > 0:
                display_columns = ['id', 'device_id', 'temperature', 'humidity', 'pressure', 'voltage', 'cpu_usage', 'received_at']
                print(df[display_columns].to_string(index=False))
            else:
                print("База данных пуста")
                
            print(f"\n📈 Всего записей: {len(df)}")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Ошибка чтения базы: {e}")

    def show_statistics(self):
        """Показывает статистику"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM renode_sensor_data")
            total_records = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT device_id) FROM renode_sensor_data")
            unique_devices = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(temperature), AVG(humidity) FROM renode_sensor_data")
            avg_data = cursor.fetchone()
            
            cursor.execute("SELECT MAX(received_at) FROM renode_sensor_data")
            last_record = cursor.fetchone()[0]
            
            print("\n📈 СТАТИСТИКА RENODE:")
            print("=" * 40)
            print(f"📋 Всего записей: {total_records}")
            print(f"📟 Уникальных устройств: {unique_devices}")
            print(f"🌡️ Средняя температура: {avg_data[0]:.2f}°C")
            print(f"💧 Средняя влажность: {avg_data[1]:.2f}%")
            print(f"🕒 Последняя запись: {last_record}")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Ошибка статистики: {e}")

if __name__ == "__main__":
    viewer = RenodeDataViewer()
    viewer.show_all_data()
    viewer.show_statistics()