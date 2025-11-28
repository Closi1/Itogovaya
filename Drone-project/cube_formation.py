import math
import time
import numpy as np
from threading import Thread, Lock
from cflib.crazyflie.swarm import Swarm
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.utils import uri_helper

class CubeFormationController:
    def __init__(self, leader_uri, follower_uris, cube_size=0.5):
        self.leader_uri = leader_uri
        self.follower_uris = follower_uris
        self.cube_size = cube_size
        
        # Позиция лидера и целевые позиции для ведомых
        self.leader_position = [0, 0, 0]
        self.target_positions = {}
        
        # Управляющие команды
        self.control_commands = {'roll': 0, 'pitch': 0, 'yaw': 0, 'thrust': 0}
        self.control_lock = Lock()
        
        # Флаги состояния
        self.is_running = False
        self.formation_active = False
        
        # Определяем позиции куба относительно лидера
        self.cube_positions = self._calculate_cube_positions()
        
    def _calculate_cube_positions(self):
        """Рассчитывает позиции вершин куба относительно центра"""
        half_size = self.cube_size / 2
        return [
            [-half_size, -half_size, -half_size],  # 0: нижний левый задний
            [half_size, -half_size, -half_size],   # 1: нижний правый задний
            [half_size, half_size, -half_size],    # 2: нижний правый передний
            [-half_size, half_size, -half_size],   # 3: нижний левый передний
            [-half_size, -half_size, half_size],   # 4: верхний левый задний
            [half_size, -half_size, half_size],    # 5: верхний правый задний
            [half_size, half_size, half_size],     # 6: верхний правый передний
            [-half_size, half_size, half_size]     # 7: верхний левый передний
        ]
    
    def _leader_position_callback(self, timestamp, data, logconf):
        """Callback для получения позиции лидера"""
        self.leader_position = [
            data['stateEstimate.x'],
            data['stateEstimate.y'], 
            data['stateEstimate.z']
        ]
        
        # Обновляем целевые позиции для ведомых
        self._update_follower_targets()
    
    def _update_follower_targets(self):
        """Обновляет целевые позиции для ведомых дронов"""
        for i, uri in enumerate(self.follower_uris):
            if i < len(self.cube_positions):
                offset = self.cube_positions[i]
                self.target_positions[uri] = [
                    self.leader_position[0] + offset[0],
                    self.leader_position[1] + offset[1], 
                    self.leader_position[2] + offset[2]
                ]
    
    def setup_leader_logging(self, scf):
        """Настраивает логирование позиции лидера"""
        log_conf = LogConfig(name='Position', period_in_ms=100)
        log_conf.add_variable('stateEstimate.x', 'float')
        log_conf.add_variable('stateEstimate.y', 'float')
        log_conf.add_variable('stateEstimate.z', 'float')
        
        scf.cf.log.add_config(log_conf)
        log_conf.data_received_cb.add_callback(self._leader_position_callback)
        log_conf.start()
    
    def follower_control_loop(self, scf):
        """Цикл управления для ведомого дрона"""
        cf = scf.cf
        uri = cf.link_uri
        
        print(f"Starting control loop for {uri}")
        
        while self.is_running:
            if self.formation_active and uri in self.target_positions:
                target = self.target_positions[uri]
                
                # Простой ПИД-регулятор для следования к целевой позиции
                current_pos = self.leader_position  # В реальности нужно получать позицию каждого дрона
                
                # Вычисляем ошибку
                error = [
                    target[0] - current_pos[0],
                    target[1] - current_pos[1],
                    target[2] - current_pos[2]
                ]
                
                # Преобразуем ошибку в команды управления (упрощенно)
                pitch = error[0] * 2.0  # Движение вперед/назад
                roll = -error[1] * 2.0  # Движение влево/вправо
                thrust = 38000 + error[2] * 1000  # Базовая тяга + коррекция высоты
                
                # Ограничиваем значения
                pitch = max(-10, min(10, pitch))
                roll = max(-10, min(10, roll))
                thrust = max(30000, min(60000, thrust))
                
                # Отправляем команды
                cf.commander.send_setpoint(roll, pitch, 0, thrust)
            
            time.sleep(0.1)
    
    def leader_control_loop(self, scf):
        """Цикл управления для лидера (ручное управление)"""
        cf = scf.cf
        
        print(f"Starting control loop for leader {self.leader_uri}")
        
        while self.is_running:
            with self.control_lock:
                roll = self.control_commands['roll']
                pitch = self.control_commands['pitch']
                yaw = self.control_commands['yaw']
                thrust = self.control_commands['thrust']
            
            # Отправляем команды лидеру
            cf.commander.send_setpoint(roll, pitch, yaw, thrust)
            time.sleep(0.1)
    
    def set_control_command(self, roll=0, pitch=0, yaw=0, thrust=0):
        """Устанавливает команды управления для лидера"""
        with self.control_lock:
            self.control_commands = {
                'roll': roll,
                'pitch': pitch,
                'yaw': yaw,
                'thrust': thrust
            }
    
    def start_formation(self):
        """Запускает формирование"""
        self.is_running = True
        self.formation_active = True
        print("Cube formation started!")
    
    def stop_formation(self):
        """Останавливает формирование"""
        self.formation_active = False
        print("Cube formation stopped!")
    
    def emergency_stop(self):
        """Аварийная остановка"""
        self.is_running = False
        self.formation_active = False
        print("EMERGENCY STOP!")

def interactive_control(controller):
    """Интерактивное управление через консоль"""
    print("\n=== Interactive Cube Formation Control ===")
    print("Commands:")
    print("  w/s: pitch (forward/backward)")
    print("  a/d: roll (left/right)")
    print("  q/e: yaw (rotate left/right)")
    print("  r/f: thrust (up/down)")
    print("  space: start formation")
    print("  x: stop formation")
    print("  c: emergency stop")
    print("  i: show info")
    print("  h: show help")
    print("  quit: exit program")
    
    import sys
    import select
    import tty
    import termios
    
    # Сохраняем настройки терминала
    old_settings = termios.tcgetattr(sys.stdin)
    
    try:
        tty.setraw(sys.stdin.fileno())
        
        base_thrust = 38000
        thrust_step = 1000
        attitude_step = 5
        
        while True:
            if select.select([sys.stdin], [], [], 0.1)[0]:
                key = sys.stdin.read(1)
                
                if key == 'q':  # Выход
                    break
                elif key == 'w':  # Вперед
                    controller.set_control_command(pitch=attitude_step)
                    print("Pitch: Forward")
                elif key == 's':  # Назад
                    controller.set_control_command(pitch=-attitude_step)
                    print("Pitch: Backward")
                elif key == 'a':  # Влево
                    controller.set_control_command(roll=-attitude_step)
                    print("Roll: Left")
                elif key == 'd':  # Вправо
                    controller.set_control_command(roll=attitude_step)
                    print("Roll: Right")
                elif key == 'q':  # Поворот влево
                    controller.set_control_command(yaw=-attitude_step)
                    print("Yaw: Left")
                elif key == 'e':  # Поворот вправо
                    controller.set_control_command(yaw=attitude_step)
                    print("Yaw: Right")
                elif key == 'r':  # Вверх
                    base_thrust += thrust_step
                    controller.set_control_command(thrust=base_thrust)
                    print(f"Thrust: {base_thrust}")
                elif key == 'f':  # Вниз
                    base_thrust -= thrust_step
                    controller.set_control_command(thrust=base_thrust)
                    print(f"Thrust: {base_thrust}")
                elif key == ' ':  # Старт формирования
                    controller.start_formation()
                    print("Formation STARTED")
                elif key == 'x':  # Стоп формирования
                    controller.stop_formation()
                    print("Formation STOPPED")
                elif key == 'c':  # Аварийная остановка
                    controller.emergency_stop()
                    break
                elif key == 'i':  # Информация
                    print(f"Leader position: {controller.leader_position}")
                    print(f"Target positions: {controller.target_positions}")
                elif key == 'h':  # Помощь
                    print("Help: w/s/a/d/q/e/r/f/space/x/c/i/h/quit")
                elif key == 'quit':
                    break
                
                # Сбрасываем команды после обработки (кроме тяги)
                current_thrust = controller.control_commands['thrust']
                if current_thrust == 0:
                    current_thrust = base_thrust
                controller.set_control_command(
                    roll=0, pitch=0, yaw=0, thrust=current_thrust
                )
    
    finally:
        # Восстанавливаем настройки терминала
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        controller.emergency_stop()

def main():
    # Инициализация драйвера
    cflib.crtp.init_drivers()
    
    # URI дронов (замените на реальные адреса ваших дронов)
    leader_uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E701')
    follower_uris = [
        uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E702'),
        uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E703'),
        uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E704'),
        # Добавьте больше URI по необходимости
    ]
    
    # Создаем контроллер
    controller = CubeFormationController(leader_uri, follower_uris, cube_size=0.3)
    
    # Создаем swarm
    uris = [leader_uri] + follower_uris
    swarm = Swarm(uris)
    
    def setup_swarm(scf):
        uri = scf.cf.link_uri
        if uri == leader_uri:
            # Настраиваем лидера
            controller.setup_leader_logging(scf)
    
    print("Connecting to drones...")
    with swarm:
        # Настраиваем swarm
        swarm.parallel_safe(setup_swarm)
        
        # Запускаем потоки управления
        threads = []
        
        # Поток для лидера
        leader_thread = Thread(target=controller.leader_control_loop, 
                             args=(swarm._cfs[leader_uri],))
        leader_thread.daemon = True
        leader_thread.start()
        threads.append(leader_thread)
        
        # Потоки для ведомых
        for uri in follower_uris:
            if uri in swarm._cfs:
                follower_thread = Thread(target=controller.follower_control_loop,
                                       args=(swarm._cfs[uri],))
                follower_thread.daemon = True
                follower_thread.start()
                threads.append(follower_thread)
        
        # Запускаем интерактивное управление
        interactive_control(controller)
        
        # Останавливаем контроллер
        controller.emergency_stop()
        
        # Ждем завершения потоков
        for thread in threads:
            thread.join(timeout=1.0)
    
    print("Program finished")

if __name__ == '__main__':
    main()