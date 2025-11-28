import socket
import time
import random
import struct
from datetime import datetime

class STM32FirmwareEmulator:
    """
    Эмулятор прошивки для STM32, которая будет работать в Renode
    Отправляет данные через TCP (как UART в Renode)
    """
    
    def __init__(self):
        self.device_id = "STM32_REAL_001"
        self.server_host = "localhost"
        self.server_port = 8888
        self.socket = None
        
    def connect_to_host(self):
        """Подключается к хосту (нашему Python серверу)"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            print(f"✅ Подключено к хосту: {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False

    def read_sensor_data(self):
        """Чтение данных с 'датчиков' (эмуляция)"""
        return {
            "device_id": self.device_id,
            "timestamp": datetime.now().isoformat(),
            "temperature": round(random.uniform(20.0, 30.0), 2),
            "humidity": round(random.uniform(40.0, 80.0), 2),
            "pressure": round(random.uniform(980.0, 1020.0), 2),
            "voltage": round(random.uniform(3.2, 3.8), 2),
            "cpu_usage": random.randint(10, 50)
        }

    def create_binary_packet(self, data):
        """Создаёт бинарный пакет в формате MCU"""
        # Заголовок пакета
        header = b'\xAA\xBB\xCC\xDD'  # 4 байта заголовка
        packet_type = b'\x02'         # Тип пакета: sensor data
        
        # Данные в бинарном формате
        device_id_bytes = data['device_id'].ljust(20).encode('utf-8')[:20]
        timestamp_bytes = data['timestamp'].ljust(30).encode('utf-8')[:30]
        
        # Числовые данные (float -> int -> bytes)
        temp_bytes = int(data['temperature'] * 100).to_bytes(2, 'little')
        humidity_bytes = int(data['humidity'] * 100).to_bytes(2, 'little')
        pressure_bytes = int(data['pressure']).to_bytes(2, 'little')
        voltage_bytes = int(data['voltage'] * 1000).to_bytes(2, 'little')
        cpu_bytes = data['cpu_usage'].to_bytes(1, 'little')
        
        # Собираем пакет
        packet = (header + packet_type + device_id_bytes + timestamp_bytes + 
                 temp_bytes + humidity_bytes + pressure_bytes + voltage_bytes + cpu_bytes)
        
        # Контрольная сумма CRC8
        checksum = self.calculate_crc8(packet)
        packet += checksum.to_bytes(1, 'little')
        
        return packet

    def calculate_crc8(self, data):
        """Вычисляет контрольную сумму CRC8"""
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

    def send_sensor_data(self):
        """Отправляет данные сенсоров"""
        try:
            sensor_data = self.read_sensor_data()
            packet = self.create_binary_packet(sensor_data)
            
            # Отправляем пакет
            self.socket.sendall(packet)
            print(f"📨 Отправлен пакет: {len(packet)} байт")
            print(f"🌡️ Данные: {sensor_data['temperature']}°C, {sensor_data['humidity']}%")
            
            # Получаем ответ
            response = self.socket.recv(1024)
            if response:
                print(f"📩 Ответ сервера: {response.decode('utf-8')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")
            return False

    def run_firmware(self):
        """Запускает эмуляцию работы прошивки"""
        print("🚀 ЗАПУСК ЭМУЛЯТОРА ПРОШИВКИ STM32")
        print(f"📟 ID устройства: {self.device_id}")
        print(f"🌐 Хост: {self.server_host}:{self.server_port}")
        print("=" * 50)
        
        if not self.connect_to_host():
            return
        
        counter = 0
        try:
            while True:
                counter += 1
                print(f"\n🔁 Отправка данных #{counter}")
                
                if self.send_sensor_data():
                    print("✅ Данные успешно отправлены!")
                else:
                    print("❌ Ошибка отправки данных!")
                
                print("⏰ Ожидание 10 секунд...")
                time.sleep(10)
                
        except KeyboardInterrupt:
            print("\n🛑 Прошивка остановлена")
        finally:
            if self.socket:
                self.socket.close()

if __name__ == "__main__":
    firmware = STM32FirmwareEmulator()
    firmware.run_firmware()