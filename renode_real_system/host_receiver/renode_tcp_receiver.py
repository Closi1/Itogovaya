import socket
import sqlite3
import struct
import threading
from datetime import datetime

class RenodeTCPReceiver:
    """
    Сервер для приёма данных от Renode через TCP
    (эмулирует подключение к UART устройства)
    """
    
    def __init__(self):
        self.host = "localhost"
        self.port = 8888
        self.db_path = "renode_sensor_data.db"
        self.setup_database()

    def setup_database(self):
        """Создаёт базу данных для данных от Renode"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS renode_sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                temperature REAL,
                humidity REAL,
                pressure REAL,
                voltage REAL,
                cpu_usage INTEGER,
                packet_size INTEGER,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'renode'
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✅ База данных создана: {self.db_path}")

    def parse_binary_packet(self, packet):
        """Парсит бинарный пакет от STM32"""
        try:
            if len(packet) < 62:  # Минимальный размер нашего пакета
                print(f"❌ Слишком короткий пакет: {len(packet)} байт")
                return None
                
            # Проверяем заголовок
            if packet[0:4] != b'\xAA\xBB\xCC\xDD':
                print("❌ Неверный заголовок пакета")
                return None
            
            # Парсим данные (little-endian как в STM32)
            device_id = packet[5:25].decode('utf-8', errors='ignore').strip()
            timestamp_str = packet[25:55].decode('utf-8', errors='ignore').strip()
            
            temperature = struct.unpack('<H', packet[55:57])[0] / 100.0
            humidity = struct.unpack('<H', packet[57:59])[0] / 100.0
            pressure = struct.unpack('<H', packet[59:61])[0]
            voltage = struct.unpack('<H', packet[61:63])[0] / 1000.0
            cpu_usage = packet[63]
            
            # Проверяем контрольную сумму
            received_checksum = packet[64]
            calculated_checksum = self.calculate_crc8(packet[:64])
            
            if received_checksum != calculated_checksum:
                print("❌ Ошибка контрольной суммы")
                return None
            
            return {
                "device_id": device_id,
                "timestamp": timestamp_str,
                "temperature": temperature,
                "humidity": humidity,
                "pressure": pressure,
                "voltage": voltage,
                "cpu_usage": cpu_usage,
                "packet_size": len(packet)
            }
            
        except Exception as e:
            print(f"❌ Ошибка парсинга пакета: {e}")
            return None

    def calculate_crc8(self, data):
        """Вычисляет CRC8 (такой же как в прошивке)"""
        crc = 0
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x07
                else:
                    crc <<= 1
                crc &= 0xFF
        return crc

    def save_to_database(self, data):
        """Сохраняет данные в SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO renode_sensor_data 
                (device_id, timestamp, temperature, humidity, pressure, voltage, cpu_usage, packet_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['device_id'],
                data['timestamp'],
                data['temperature'],
                data['humidity'],
                data['pressure'],
                data['voltage'],
                data['cpu_usage'],
                data['packet_size']
            ))
            
            conn.commit()
            conn.close()
            print(f"💾 Данные от Renode сохранены: {data['device_id']}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
            return False

    def handle_client(self, client_socket, address):
        """Обрабатывает подключение клиента"""
        print(f"🔌 Подключился клиент: {address}")
        
        try:
            while True:
                # Получаем данные
                data = client_socket.recv(1024)
                if not data:
                    break
                
                print(f"📥 Получено {len(data)} байт от {address}")
                
                # Парсим пакет
                sensor_data = self.parse_binary_packet(data)
                
                if sensor_data:
                    # Сохраняем в базу
                    self.save_to_database(sensor_data)
                    
                    # Отправляем подтверждение
                    response = f"ACK: Data received from {sensor_data['device_id']}\n"
                    client_socket.send(response.encode('utf-8'))
                    print(f"📨 Отправлен ответ: {response.strip()}")
                else:
                    response = "ERROR: Invalid packet format\n"
                    client_socket.send(response.encode('utf-8'))
                    
        except Exception as e:
            print(f"❌ Ошибка обработки клиента: {e}")
        finally:
            client_socket.close()
            print(f"🔒 Клиент отключен: {address}")

    def start_server(self):
        """Запускает TCP сервер"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            
            print("🖥️ RENODE TCP СЕРВЕР ЗАПУЩЕН")
            print(f"📍 Адрес: {self.host}:{self.port}")
            print(f"💾 База данных: {self.db_path}")
            print("=" * 50)
            print("⏳ Ожидаем подключения Renode...")
            
            while True:
                client_socket, address = server_socket.accept()
                
                # Обрабатываем каждого клиента в отдельном потоке
                client_thread = threading.Thread(
                    target=self.handle_client, 
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
                
        except KeyboardInterrupt:
            print("\n🛑 Сервер остановлен")
        except Exception as e:
            print(f"❌ Ошибка сервера: {e}")
        finally:
            server_socket.close()

if __name__ == "__main__":
    receiver = RenodeTCPReceiver()
    receiver.start_server()