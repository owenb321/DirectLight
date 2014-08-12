import subprocess as sp
import os
import re

scriptDir = os.path.dirname(os.path.realpath(__file__))
ffmpeg_bin = scriptDir + r'/ffmpeg.exe'
os.system(ffmpeg_bin + " -list_devices true -f dshow -i dummy > " + scriptDir + "/devices.txt 2>&1")

readDevices = False
devices = []
with open(scriptDir + "/devices.txt") as fp:
    for line in fp:
        if readDevices:
            m = re.match(r'\[dshow @ \w+]  "(.*?)"\n+', line)
            if m is None:
                break
            devices.append(m.group(1))
        if "DirectShow video devices" in line:
            readDevices = True
            
file = open(scriptDir + "/devices.txt", 'w')
for i, device in enumerate(devices):
    file.write(str(i) + " - " +str(device)+"\n")