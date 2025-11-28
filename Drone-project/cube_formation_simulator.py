# cube_formation_simulator.py
import time
import math
import sys
import os

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем наш симулятор вместо реальной библиотеки
import drone_simulator as sim

# Переопределяем импорты для использования симулятора
cflib = sim
Swarm = sim.SimulatedSwarm
SyncCrazyflie = sim.SimulatedSyncCrazyflie

class LogConfig:
    """Класс для конфигурации логирования"""
    def __init__(self, name, period_in_ms):
        self.name = name
        self.period_in_ms = period_in_ms
        self.variables = []
        self.data_received_cb = CallbackContainer()
    
    def add_variable(self, variable, type):
        self.variables.append(variable)
    
    def start(self):
        pass

class CallbackContainer:
    """Контейнер для callback функций"""
    def __init__(self):
        self.callbacks = []
    
    def add_callback(self, callback):
        self.callbacks.append(callback)

class CubeFormationController:
    def __init__(self, leader_uri, follower_uris, cube_size=0.5):
        self.leader_uri = leader_uri
        self.follower_uris = follower_uris
        self.cube_size = cube_size
        
        self.leader_position = [0, 0, 0]
        self.target_positions = {}
        self.is_running = False
        self.formation_active = False
        
        # Рассчитываем позиции куба
        self.cube_positions = self._calculate_cube_positions()
        
        # Настраиваем колбэки для позиций
        self._setup_position_callbacks()
    
    def _calculate_cube_positions(self):
        """Рассчитывает позиции вершин куба"""
        half_size = self.cube_size / 2
        return [
            [-half_size, -half_size, -half_size],  # 0
            [half_size, -half_size, -half_size],   # 1
            [half_size, half_size, -half_size],    # 2
            [-half_size, half_size, -half_size],   # 3
            [-half_size, -half_size, half_size],   # 4
            [half_size, -half_size, half_size],    # 5
            [half_size, half_size, half_size],     # 6
            [-half_size, half_size, half_size]     # 7
        ]
    
    def _setup_position_callbacks(self):
        """Настраиваем callback'и для получения позиций"""
        # Для лидера
        def leader_callback(timestamp, data, logconf):
            self.leader_position = [
                data['stateEstimate.x'],
                data['stateEstimate.y'],
                data['stateEstimate.z']
            ]
            self._update_follower_targets()
        
        sim.simulator.add_position_callback(self.leader_uri, leader_callback)
        
        # Для ведомых (если нужно отслеживать их позиции)
        for uri in self.follower_uris:
            def follower_callback(timestamp, data, logconf, drone_uri=uri):
                # Можно добавить логику для отслеживания ведомых
                pass
            sim.simulator.add_position_callback(uri, follower_callback)
    
    def _update_follower_targets(self):
        """Обновляет целевые позиции для ведомых дронов"""
        for i, uri in enumerate(self.follower_uris):
            if i < len(self.cube_positions):
                offset = self.cube_positions[i]
                self.target_positions[uri] = [
                    self.leader_position[0] + offset[0],
                    self.leader_position[1] + offset[1],
                    max(0.1, self.leader_position[2] + offset[2])  # Не ниже 0.1м
                ]
    
    def setup_leader_logging(self, scf):
        """Настраиваем логирование для лидера (заглушка)"""
        print(f"Logging setup for {scf.cf.link_uri}")
    
    def follower_control_loop(self, scf):
        """Цикл управления для ведомого дрона"""
        cf = scf.cf
        uri = cf.link_uri
        
        print(f"Starting control for follower: {uri}")
        
        base_height = 0.5
        takeoff_time = time.time() + 2  # Взлет через 2 секунды
        
        while self.is_running:
            current_time = time.time()
            
            if current_time < takeoff_time:
                # Фаза подготовки - на земле
                cf.commander.send_hover_setpoint(0, 0, 0, 0)
            else:
                # Фаза полета
                if self.formation_active and uri in self.target_positions:
                    target = self.target_positions[uri]
                    
                    # Добавляем базовую высоту к Z-координате
                    target_z = target[2] + base_height
                    
                    # Отправляем команду позиции
                    cf.commander.send_position_setpoint(
                        target[0], target[1], target_z, 0
                    )
                else:
                    # Просто зависание
                    cf.commander.send_hover_setpoint(0, 0, 0, base_height)
            
            time.sleep(0.1)
    
    def leader_control_loop(self, scf):
        """Цикл управления для лидера"""
        cf = scf.cf
        uri = cf.link_uri
        
        print(f"Starting control for leader: {uri}")
        
        base_height = 0.5
        takeoff_time = time.time() + 2
        
        # Начальная позиция лидера
        initial_leader_pos = [0, 0, base_height]
        sim.simulator.set_target_position(uri, initial_leader_pos)
        
        while self.is_running:
            current_time = time.time()
            
            if current_time < takeoff_time:
                # На земле
                cf.commander.send_hover_setpoint(0, 0, 0, 0)
            else:
                # В полете - лидер просто зависает
                cf.commander.send_hover_setpoint(0, 0, 0, base_height)
            
            time.sleep(0.1)
    
    def start_formation(self):
        """Запускает формирование"""
        self.is_running = True
        self.formation_active = True
        print("✓ Cube formation started!")
    
    def stop_formation(self):
        """Останавливает формирование"""
        self.formation_active = False
        print("✓ Cube formation stopped!")
    
    def emergency_stop(self):
        """Аварийная остановка"""
        self.is_running = False
        self.formation_active = False
        print("✓ Emergency stop!")

def interactive_control(controller):
    """Интерактивное управление через консоль"""
    import threading
    
    print("\n" + "="*50)
    print("      CUBE FORMATION SIMULATOR")
    print("="*50)
    print("Controls:")
    print("  SPACE - Start/Stop formation")
    print("  W/S   - Move leader forward/backward")
    print("  A/D   - Move leader left/right") 
    print("  R/F   - Move leader up/down")
    print("  Q     - Quit")
    print("="*50)
    
    def input_thread():
        while controller.is_running:
            try:
                key = input().lower()
                
                if key == ' ':
                    if controller.formation_active:
                        controller.stop_formation()
                        print("Formation STOPPED")
                    else:
                        controller.start_formation()
                        print("Formation STARTED")
                
                elif key == 'w':
                    # Движение вперед
                    new_pos = [
                        controller.leader_position[0] + 0.2,
                        controller.leader_position[1],
                        controller.leader_position[2]
                    ]
                    sim.simulator.set_target_position(controller.leader_uri, new_pos)
                    print("Leader: FORWARD")
                
                elif key == 's':
                    # Движение назад
                    new_pos = [
                        controller.leader_position[0] - 0.2,
                        controller.leader_position[1],
                        controller.leader_position[2]
                    ]
                    sim.simulator.set_target_position(controller.leader_uri, new_pos)
                    print("Leader: BACKWARD")
                
                elif key == 'a':
                    # Движение влево
                    new_pos = [
                        controller.leader_position[0],
                        controller.leader_position[1] - 0.2,
                        controller.leader_position[2]
                    ]
                    sim.simulator.set_target_position(controller.leader_uri, new_pos)
                    print("Leader: LEFT")
                
                elif key == 'd':
                    # Движение вправо
                    new_pos = [
                        controller.leader_position[0],
                        controller.leader_position[1] + 0.2,
                        controller.leader_position[2]
                    ]
                    sim.simulator.set_target_position(controller.leader_uri, new_pos)
                    print("Leader: RIGHT")
                
                elif key == 'r':
                    # Вверх
                    new_pos = [
                        controller.leader_position[0],
                        controller.leader_position[1],
                        controller.leader_position[2] + 0.2
                    ]
                    sim.simulator.set_target_position(controller.leader_uri, new_pos)
                    print("Leader: UP")
                
                elif key == 'f':
                    # Вниз
                    new_pos = [
                        controller.leader_position[0],
                        controller.leader_position[1],
                        max(0.1, controller.leader_position[2] - 0.2)
                    ]
                    sim.simulator.set_target_position(controller.leader_uri, new_pos)
                    print("Leader: DOWN")
                
                elif key == 'q':
                    controller.emergency_stop()
                    break
                    
            except Exception as e:
                print(f"Input error: {e}")
                break
    
    # Запускаем поток для ввода
    input_thread = threading.Thread(target=input_thread)
    input_thread.daemon = True
    input_thread.start()

def main():
    print("Initializing Cube Formation Simulator...")
    
    # Инициализируем симулятор
    sim.init_drivers()
    
    # Сканируем доступные дроны
    available_drones = sim.scan_interfaces()
    available_uris = [drone[0] for drone in available_drones]
    
    if not available_uris:
        print("No drones found!")
        return
    
    print(f"Available drones: {len(available_uris)}")
    for uri in available_uris:
        print(f"  - {uri}")
    
    # Выбираем лидера и ведомых
    leader_uri = available_uris[0]
    follower_uris = available_uris[1:]  # Все остальные - ведомые
    
    print(f"Leader: {leader_uri}")
    print(f"Followers: {follower_uris}")
    
    # Создаем контроллер
    controller = CubeFormationController(leader_uri, follower_uris, cube_size=0.4)
    
    # Запускаем симулятор
    sim.simulator.start()
    
    # Создаем swarm
    all_uris = [leader_uri] + follower_uris
    swarm = Swarm(all_uris)
    
    try:
        with swarm:
            # Настраиваем логирование
            swarm.parallel_safe(controller.setup_leader_logging)
            
            # Запускаем управление
            import threading
            
            # Поток для лидера
            leader_thread = threading.Thread(
                target=controller.leader_control_loop,
                args=(swarm._cfs[leader_uri],)
            )
            leader_thread.daemon = True
            leader_thread.start()
            
            # Потоки для ведомых
            follower_threads = []
            for uri in follower_uris:
                thread = threading.Thread(
                    target=controller.follower_control_loop,
                    args=(swarm._cfs[uri],)
                )
                thread.daemon = True
                thread.start()
                follower_threads.append(thread)
            
            # Запускаем формирование
            controller.start_formation()
            
            # Интерактивное управление
            interactive_control(controller)
            
            # Останавливаем
            controller.emergency_stop()
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sim.simulator.stop()
        print("Simulation finished!")

if __name__ == '__main__':
    main()