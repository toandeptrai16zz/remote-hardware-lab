import glob
print(glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*'))
