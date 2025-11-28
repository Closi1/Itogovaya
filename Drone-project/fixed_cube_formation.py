# fixed_cube_formation.py
import time
import math
import sys
import os
import threading

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем симулятор
import fixed_simulator as sim

class LogConfig:
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
    def __init__(self):
        self.callbacks = []
    
    def add_callback(self, callback):
        self.callbacks.append(callback)

class CubeFormationController:
    def __init__(self, leader_uri, follower_uris, cube_size=0.5):
        self.leader_uri = leader_uri
        self.follower_uris = follower_uris
        self.cube_size = cube_size
        
        self.leader_position = [0, 0, 0.5]  # Начинаем с высоты 0.5м
        self.target_positions = {}
        self.is_running = True  # Сразу запускаем
        self.formation_active = True  # Сразу активируем формирование
        
        self.cube_positions = self._calculate_cube_positions()
        self._setup_position_callbacks()
        
        # Устанавливаем начальную позицию лидера
        sim.simulator.set_target_position(leader_uri, self.leader_position)
    
    def _calculate_cube_positions(self):
        half_size = self.cube_size / 2
        return [
            [-half_size, -half_size, 0],  # 0
            [half_size, -half_size, 0],   # 1
            [half_size, half_size, 0],    # 2
            [-half_size, half_size, 0],   # 3
            [-half_size, -half_size, half_size],  # 4
            [half_size, -half_size, half_size],   # 5
            [half_size, half_size, half_size],    # 6
            [-half_size, half_size, half_size]    # 7
        ]
    
    def _setup_position_callbacks(self):
        def leader_callback(timestamp, data, logconf):
            self.leader_position = [
                data['stateEstimate.x'],
                data['stateEstimate.y'],
                data['stateEstimate.z']
            ]
            self._update_follower_targets()
        
        sim.simulator.add_position_callback(self.leader_uri, leader_callback)
        
        for uri in self.follower_uris:
            def follower_callback(timestamp, data, logconf, drone_uri=uri):
                pass
            sim.simulator.add_position_callback(uri, follower_callback)
    
    def _update_follower_targets(self):
        for i, uri in enumerate(self.follower_uris):
            if i < len(self.cube_positions):
                offset = self.cube_positions[i]
                self.target_positions[uri] = [
                    self.leader_position[0] + offset[0],
                    self.leader_position[1] + offset[1],
                    max(0.3, self.leader_position[2] + offset[2])
                ]
    
    def setup_leader_logging(self, scf):
        print(f"Logging setup for {scf.uri}")
    
    def follower_control_loop(self, scf):
        uri = scf.uri
        
        print(f"Starting control for follower: {uri}")
        
        # Подключаем дрон
        sim.simulator.connect_drone(uri)
        
        base_height = 0.5
        
        while self.is_running:
            if self.formation_active and uri in self.target_positions:
                target = self.target_positions[uri]
                
                # Используем commander для установки позиции
                commander = sim.SimulatedCommander(sim.simulator.drones[uri], sim.simulator)
                commander.send_position_setpoint(
                    target[0], target[1], target[2], 0
                )
            else:
                # Зависание на месте
                commander = sim.SimulatedCommander(sim.simulator.drones[uri], sim.simulator)
                commander.send_hover_setpoint(0, 0, 0, base_height)
            
            time.sleep(0.1)
    
    def leader_control_loop(self, scf):
        uri = scf.uri
        
        print(f"Starting control for leader: {uri}")
        
        # Подключаем дрон
        sim.simulator.connect_drone(uri)
        
        base_height = 0.5
        
        while self.is_running:
            # Лидер просто зависает на месте
            commander = sim.SimulatedCommander(sim.simulator.drones[uri], sim.simulator)
            commander.send_hover_setpoint(0, 0, 0, base_height)
            
            time.sleep(0.1)
    
    def move_leader(self, direction):
        """Двигаем лидера в указанном направлении"""
        move_distance = 0.3
        
        if direction == 'forward':
            self.leader_position[0] += move_distance
        elif direction == 'backward':
            self.leader_position[0] -= move_distance
        elif direction == 'left':
            self.leader_position[1] -= move_distance
        elif direction == 'right':
            self.leader_position[1] += move_distance
        elif direction == 'up':
            self.leader_position[2] += move_distance
        elif direction == 'down':
            self.leader_position[2] = max(0.3, self.leader_position[2] - move_distance)
        
        # Обновляем позицию в симуляторе
        sim.simulator.set_target_position(self.leader_uri, self.leader_position)
        print(f"Leader moved {direction}: {self.leader_position}")
    
    def toggle_formation(self):
        self.formation_active = not self.formation_active
        status = "STARTED" if self.formation_active else "STOPPED"
        print(f"Formation {status}")
    
    def emergency_stop(self):
        self.is_running = False
        print("Emergency stop!")

def print_status(controller):
    """Печатает текущий статус дронов"""
    while controller.is_running:
        print("\n" + "="*50)
        print("DRONE POSITIONS:")
        print(f"Leader {controller.leader_uri}: {controller.leader_position}")
        
        for i, uri in enumerate(controller.follower_uris):
            if i < len(controller.cube_positions):
                offset = controller.cube_positions[i]
                target_pos = controller.target_positions.get(uri, [0, 0, 0])
                actual_pos = sim.simulator.get_position(uri) or [0, 0, 0]
                print(f"Follower {uri}:")
                print(f"  Target: {[round(x, 2) for x in target_pos]}")
                print(f"  Actual: {[round(x, 2) for x in actual_pos]}")
                print(f"  Offset: {[round(x, 2) for x in offset]}")
        
        print("="*50)
        time.sleep(3)

def interactive_control():
    """Упрощенное интерактивное управление"""
    print("\n" + "="*50)
    print("      CUBE FORMATION SIMULATOR")
    print("="*50)
    print("Controls:")
    print("  1 - Move leader FORWARD")
    print("  2 - Move leader BACKWARD") 
    print("  3 - Move leader LEFT")
    print("  4 - Move leader RIGHT")
    print("  5 - Move leader UP")
    print("  6 - Move leader DOWN")
    print("  7 - Toggle formation (Start/Stop)")
    print("  8 - Show drone positions")
    print("  0 - QUIT")
    print("="*50)
    
    while True:
        try:
            choice = input("\nEnter choice (0-8): ").strip()
            
            if choice == '0':
                print("Exiting...")
                break
            elif choice == '1':
                controller.move_leader('forward')
            elif choice == '2':
                controller.move_leader('backward')
            elif choice == '3':
                controller.move_leader('left')
            elif choice == '4':
                controller.move_leader('right')
            elif choice == '5':
                controller.move_leader('up')
            elif choice == '6':
                controller.move_leader('down')
            elif choice == '7':
                controller.toggle_formation()
            elif choice == '8':
                # Показываем позиции в следующем обновлении статуса
                print("Positions will be shown in next status update...")
            else:
                print("Invalid choice! Please enter 0-8")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    global controller
    
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
    follower_uris = available_uris[1:4]  # Берем максимум 3 ведомых для куба
    
    print(f"Leader: {leader_uri}")
    print(f"Followers: {follower_uris}")
    
    # Создаем контроллер
    controller = CubeFormationController(leader_uri, follower_uris, cube_size=0.4)
    
    # Запускаем симулятор
    sim.simulator.start()
    
    # Запускаем потоки управления дронами
    threads = []
    
    # Поток для лидера
    leader_thread = threading.Thread(
        target=controller.leader_control_loop,
        args=(sim.SimulatedSyncCrazyflie(leader_uri),)
    )
    leader_thread.daemon = True
    leader_thread.start()
    threads.append(leader_thread)
    
    # Потоки для ведомых
    for uri in follower_uris:
        follower_thread = threading.Thread(
            target=controller.follower_control_loop,
            args=(sim.SimulatedSyncCrazyflie(uri),)
        )
        follower_thread.daemon = True
        follower_thread.start()
        threads.append(follower_thread)
    
    # Поток для отображения статуса
    status_thread = threading.Thread(target=print_status, args=(controller,))
    status_thread.daemon = True
    status_thread.start()
    
    print("\nSimulation is running! Drones are forming a cube...")
    print("You can now control the leader drone.")
    
    try:
        # Запускаем интерактивное управление
        interactive_control()
    finally:
        # Останавливаем все
        controller.emergency_stop()
        sim.simulator.stop()
        print("Simulation finished!")

if __name__ == '__main__':
    main()