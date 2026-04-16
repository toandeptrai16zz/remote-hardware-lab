import serial
import traceback

try:
    s = serial.Serial('/dev/ttyUSB0')
    s.close()
    print("Success")
except Exception as e:
    print(f"Failed opening port /dev/ttyUSB0")
    print(f"Exception Type: {type(e)}")
    print(f"Exception Message: {str(e)}")
    traceback.print_exc()
