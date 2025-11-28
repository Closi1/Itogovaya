import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.utils import uri_helper

def find_drones():
    cflib.crtp.init_drivers()
    print("Scanning for drones...")
    
    found = cflib.crtp.scan_interfaces()
    
    if not found:
        print("No drones found! Check:")
        print("1. Дроны включены")
        print("2. Crazyradio PA подключен")
        print("3. Батареи заряжены")
        return
    
    print(f"Found {len(found)} drones:")
    for i, drone in enumerate(found):
        print(f"{i+1}. URI: {drone[0]}")
    
    return [drone[0] for drone in found]

if __name__ == '__main__':
    find_drones()