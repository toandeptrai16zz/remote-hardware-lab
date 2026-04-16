import glob
import serial
import traceback

raw_ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
active_ports = []
print("Raw ports:", raw_ports)

for port in raw_ports:
    try:
        s = serial.Serial(port)
        s.close()
        active_ports.append(port)
        print("Success:", port)
    except Exception as e:
        error_str = str(e).lower()
        print("Exception for", port, ":", error_str)
        if 'busy' in error_str or 'permission' in error_str:
            active_ports.append(port)

print("Active ports:", active_ports)
