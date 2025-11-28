# fixed_simulator.py
import time
import math
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Any
import random

@dataclass
class SimulatedDrone:
    uri: str
    position: List[float]
    connected: bool = False
    is_flying: bool = False
    
    def __post_init__(self):
        self.position = self.position.copy()

class SimulatedCommander:
    def __init__(self, drone: SimulatedDrone, simulator):
        self.drone = drone
        self.simulator = simulator
    
    def send_position_setpoint(self, x: float, y: float, z: float, yaw: float):
        self.simulator.set_target_position(self.drone.uri, [x, y, z])
    
    def send_hover_setpoint(self, vx: float, vy: float, yawrate: float, zdistance: float):
        current_pos = self.drone.position
        self.simulator.set_target_position(self.drone.uri, [current_pos[0], current_pos[1], zdistance])
    
    def send_stop_setpoint(self):
        self.simulator.stop_drone(self.drone.uri)

class SimulatedLog:
    def __init__(self):
        self.configs = []
    
    def add_config(self, log_conf):
        self.configs.append(log_conf)

class SimulatedCrazyflie:
    def __init__(self, uri: str, simulator):
        self.link_uri = uri
        self.simulator = simulator
        self.drone = simulator.drones[uri]
        self.commander = SimulatedCommander(self.drone, simulator)
        self.log = SimulatedLog()

class SimulatedSyncCrazyflie:
    def __init__(self, uri, cf=None):
        self.cf = cf
        self.uri = uri
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

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
        if initial_pos is None:
            initial_pos = [0, 0, 0]
        
        self.drones[uri] = SimulatedDrone(uri, initial_pos, connected=False)
        self.target_positions[uri] = initial_pos.copy()
        print(f"✓ Simulated drone added: {uri} at {initial_pos}")
    
    def connect_drone(self, uri: str):
        if uri in self.drones:
            self.drones[uri].connected = True
            self.drones[uri].is_flying = True
    
    def set_target_position(self, uri: str, target_pos: List[float]):
        if uri in self.drones:
            self.target_positions[uri] = target_pos.copy()
    
    def stop_drone(self, uri: str):
        if uri in self.drones:
            current_pos = self.drones[uri].position
            self.target_positions[uri] = current_pos.copy()
    
    def get_position(self, uri: str) -> Optional[List[float]]:
        if uri in self.drones:
            return self.drones[uri].position.copy()
        return None
    
    def add_position_callback(self, uri: str, callback: Callable):
        if uri not in self.callbacks:
            self.callbacks[uri] = []
        self.callbacks[uri].append(callback)
    
    def _update_loop(self):
        while self.running:
            for uri, drone in self.drones.items():
                if drone.connected and drone.is_flying:
                    target = self.target_positions[uri]
                    current = drone.position
                    
                    speed = 0.1
                    dx = target[0] - current[0]
                    dy = target[1] - current[1]
                    dz = target[2] - current[2]
                    
                    drone.position[0] += dx * speed
                    drone.position[1] += dy * speed
                    drone.position[2] += dz * speed
                    
                    if uri in self.callbacks:
                        for callback in self.callbacks[uri]:
                            log_data = {
                                'stateEstimate.x': drone.position[0],
                                'stateEstimate.y': drone.position[1],
                                'stateEstimate.z': drone.position[2]
                            }
                            callback(time.time(), log_data, None)
            
            time.sleep(0.1)
    
    def start(self):
        if not self.running:
            self.running = True
            self.update_thread = threading.Thread(target=self._update_loop)
            self.update_thread.daemon = True
            self.update_thread.start()
            print("✓ Local simulator started")
    
    def stop(self):
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=1.0)
        print("✓ Local simulator stopped")

simulator = LocalSimulator()

def init_drivers():
    print("✓ Simulated drivers initialized")
    return True

def scan_interfaces():
    uris = [
        'radio://0/80/2M/E7E7E7E701',
        'radio://0/80/2M/E7E7E7E702', 
        'radio://0/80/2M/E7E7E7E703',
        'radio://0/80/2M/E7E7E7E704'
    ]
    
    for i, uri in enumerate(uris):
        simulator.add_drone(uri, [i * 0.5, 0, 0])
    
    print(f"✓ Found {len(uris)} simulated drones")
    return [(uri, f"Simulated Drone {i+1}") for i, uri in enumerate(uris)]