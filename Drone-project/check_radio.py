import usb.core
import usb.backend.libusb1
import sys

def check_usb_devices():
    print("=== Checking USB Devices ===")
    
    # Попробуем найти бэкенд
    try:
        backend = usb.backend.libusb1.get_backend()
        if backend:
            print("✓ libusb backend found")
        else:
            print("✗ libusb backend not found")
            return False
    except Exception as e:
        print(f"✗ Error getting backend: {e}")
        return False
    
    # Поиск Crazyradio
    try:
        # Crazyradio PA
        devices = usb.core.find(idVendor=0x1915, idProduct=0x7777, find_all=True)
        crazyradios = list(devices) if devices else []
        
        # Старый Crazyradio
        devices_old = usb.core.find(idVendor=0x1915, idProduct=0x7776, find_all=True)
        crazyradios_old = list(devices_old) if devices_old else []
        
        all_radios = crazyradios + crazyradios_old
        
        if all_radios:
            print(f"✓ Found {len(all_radios)} Crazyradio device(s):")
            for i, radio in enumerate(all_radios):
                print(f"  {i+1}. Vendor: 0x{radio.idVendor:04x}, Product: 0x{radio.idProduct:04x}")
            return True
        else:
            print("✗ No Crazyradio devices found")
            return False
            
    except Exception as e:
        print(f"✗ Error searching for devices: {e}")
        return False

def check_python_environment():
    print("\n=== Checking Python Environment ===")
    try:
        import cflib
        print("✓ cflib installed")
    except ImportError:
        print("✗ cflib not installed")
        return False
    
    try:
        import usb
        print("✓ pyusb installed")
    except ImportError:
        print("✗ pyusb not installed")
        return False
        
    return True

if __name__ == "__main__":
    print("Python version:", sys.version)
    print()
    
    env_ok = check_python_environment()
    print()
    radio_ok = check_usb_devices()
    
    print("\n=== Summary ===")
    if env_ok and radio_ok:
        print("✓ System ready for Crazyflie")
    else:
        print("✗ System configuration issues detected")
        
        if not env_ok:
            print("  - Fix Python package installation")
        if not radio_ok:
            print("  - Check Crazyradio connection and drivers")