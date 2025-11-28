# drone_simulator.py
import time
import math
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
import random

@dataclass
class SimulatedDrone:
    uri: str
    position: List[float]  # [x, y, z]
    connected: bool = False
    is_flying: bool = False
    
    def __post_init__(self):
        self.position = self.position.copy()

class SimulatedCommander:
    def __init__(self, drone: SimulatedDrone, simulator):
        self.drone = drone
        self.simulator = simulator
    
    def send_position_setpoint(self, x: float, y: float, z: float, yaw: float):
        """Отправляем команду позиции дрону"""
        target_pos = [x, y, z]
        self.simulator.set_target_position(self.drone.uri, target_pos)
    
    def send_hover_setpoint(self, vx: float, vy: float, yawrate: float, zdistance: float):
        """Отправляем команду зависания"""
        current_pos = self.drone.position
        target_pos = [current_pos[0], current_pos[1], zdistance]
        self.simulator.set_target_position(self.drone.uri, target_pos)
    
    def send_stop_setpoint(self):
        """Останавливаем дрон"""
        self.simulator.stop_drone(self.drone.uri)

class SimulatedCrazyflie:
    def __init__(self, uri: str, simulator):
        self.link_uri = uri
        self.simulator = simulator
        self.commander = SimulatedCommander(self.simulator.drones[uri], simulator)
        self.log = SimulatedLog()

class SimulatedLog:
    def __init__(self):
        self.configs = []
    
    def add_config(self, log_conf):
        self.configs.append(log_conf)

class SimulatedSyncCrazyflie:
    def __init__(self, uri, cf=None):
        self.cf = cf or SimulatedCrazyflie(uri, simulator)
        self._is_open = False
    
    def __enter__(self):
        self.open_link()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_link()
    
    def open_link(self):
        self._is_open = True
        simulator.connect_drone(self.cf.link_uri)
    
    def close_link(self):
        self._is_open = True

class SimulatedSwarm:
    def __init__(self, uris):
        self.uris = uris
        self._cfs = {}
        for uri in uris:
            self._cfs[uri] = SimulatedSyncCrazyflie(uri)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def parallel_safe(self, func):
        """Выполняет функцию для каждого дрона"""
        for uri in self.uris:
            scf = self._cfs[uri]
            func(scf)

class LocalSimulator:
    def __init__(self):
        self.drones: Dict[str, SimulatedDrone] = {}
        self.target_positions: Dict[str, List[float]] = {}
        self.running = False
        self.update_thread = None
        self.callbacks: Dict[str, List[Callable]] = {}
        
    def add_drone(self, uri: str, initial_pos: List[float] = None):
        """Добавляем дрон в симулятор"""
        if initial_pos is None:
            initial_pos = [0, 0, 0]
        
        self.drones[uri] = SimulatedDrone(uri, initial_pos, connected=False)
        self.target_positions[uri] = initial_pos.copy()
        print(f"✓ Simulated drone added: {uri} at {initial_pos}")
    
    def connect_drone(self, uri: str):
        """Подключаем дрон"""
        if uri in self.drones:
            self.drones[uri].connected = True
            self.drones[uri].is_flying = True
    
    def set_target_position(self, uri: str, target_pos: List[float]):
        """Устанавливаем целевую позицию для дрона"""
        if uri in self.drones:
            self.target_positions[uri] = target_pos.copy()
    
    def stop_drone(self, uri: str):
        """Останавливаем дрон"""
        if uri in self.drones:
            current_pos = self.drones[uri].position
            self.target_positions[uri] = current_pos.copy()
    
    def get_position(self, uri: str) -> Optional[List[float]]:
        """Получаем текущую позицию дрона"""
        if uri in self.drones:
            return self.drones[uri].position.copy()
        return None
    
    def add_position_callback(self, uri: str, callback: Callable):
        """Добавляем callback для обновления позиции"""
        if uri not in self.callbacks:
            self.callbacks[uri] = []
        self.callbacks[uri].append(callback)
    
    def _update_loop(self):
        """Основной цикл обновления симуляции"""
        while self.running:
            for uri, drone in self.drones.items():
                if drone.connected and drone.is_flying:
                    target = self.target_positions[uri]
                    current = drone.position
                    
                    # Плавное движение к целевой позиции
                    speed = 0.1
                    dx = target[0] - current[0]
                    dy = target[1] - current[1]
                    dz = target[2] - current[2]
                    
                    # Обновляем позицию
                    drone.position[0] += dx * speed
                    drone.position[1] += dy * speed
                    drone.position[2] += dz * speed
                    
                    # Вызываем колбэки для логирования
                    if uri in self.callbacks:
                        for callback in self.callbacks[uri]:
                            # Имитируем данные для логирования
                            log_data = {
                                'stateEstimate.x': drone.position[0],
                                'stateEstimate.y': drone.position[1],
                                'stateEstimate.z': drone.position[2]
                            }
                            callback(time.time(), log_data, None)
            
            time.sleep(0.1)  # 10 Hz update rate
    
    def start(self):
        """Запускаем симулятор"""
        if not self.running:
            self.running = True
            self.update_thread = threading.Thread(target=self._update_loop)
            self.update_thread.daemon = True
            self.update_thread.start()
            print("✓ Local simulator started")
    
    def stop(self):
        """Останавливаем симулятор"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=1.0)
        print("✓ Local simulator stopped")

# Глобальный экземпляр симулятора
simulator = LocalSimulator()

# Имитируем cflib функции для совместимости
def init_drivers():
    """Имитация инициализации драйверов"""
    print("✓ Simulated drivers initialized")
    return True

def scan_interfaces():
    """Имитация поиска дронов"""
    uris = [
        'radio://0/80/2M/E7E7E7E701',
        'radio://0/80/2M/E7E7E7E702', 
        'radio://0/80/2M/E7E7E7E703',
        'radio://0/80/2M/E7E7E7E704'
    ]
    
    # Добавляем дроны в симулятор
    for i, uri in enumerate(uris):
        simulator.add_drone(uri, [i * 0.5, 0, 0])
    
    print(f"✓ Found {len(uris)} simulated drones")
    return [(uri, f"Simulated Drone {i+1}") for i, uri in enumerate(uris)]