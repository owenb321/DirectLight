import numpy
import cv2
import lightpack
import time
import ConfigParser
import os
import sys
import subprocess as sp
from _winreg import *
import captureInput
import threading

PRISMATIK = 0
AMBIBOX = 1

class DirectLight(object):

    def __init__(self):
        self.scriptDir = os.path.dirname(os.path.realpath(__file__))
        self.ResetPreferences()
        
    def ResetPreferences(self):
        config = ConfigParser.ConfigParser()
        
        if os.path.isfile(self.scriptDir + '/DirectLight.ini'):
            self.serverType = PRISMATIK
            config.read(self.scriptDir + '/DirectLight.ini')
        else:
            self.serverType = AMBIBOX
            config.read(sys.path[-1] + '/DirectLight.ini')
            
        print 'serverType: ' + str(self.serverType)
        
        self.host = config.get('Lightpack', 'host')
        self.port = config.getint('Lightpack', 'port')
        
        self.lpack = lightpack.lightpack(self.host, self.port) 
        
        #default capture values
        self.videoX = config.getint('Capture', 'videoWidth')
        self.videoY = config.getint('Capture', 'videoHeight')
        self.videoFps = config.getfloat('Capture', 'videoFramerate')
        self.videoDevice = config.getint('Capture', 'videoDevice')
        self.videoDeviceName = config.get('Capture', 'videoDeviceName')
        
        self.videoRenderX = config.getint('Render', 'renderWidth')
        self.videoRenderY = config.getint('Render', 'renderHeight')
        
        if self.serverType == PRISMATIK:
            self.screenX = config.getint('Display', 'displayWidth')
            self.screenY = config.getint('Display', 'displayHeight')
        else:
            self.screenX = 10000
            self.screenY = 10000
            
        self.cropTop = config.getint('Cropping', 'cropTop')
        self.cropBottom = config.getint('Cropping', 'cropBottom')
        self.cropLeft = config.getint('Cropping', 'cropLeft')
        self.cropRight = config.getint('Cropping', 'cropRight')
        
        tempServerType = config.get('Switches', 'serverType')
        self.serverType = AMBIBOX if tempServerType.strip() == 'ambibox' else PRISMATIK
        self.useFfmpeg = config.getboolean('Switches', 'useFfmpeg')
        self.labColorspace = config.getboolean('Switches', 'labColorspace')
        self.enableStandby = config.getboolean('Switches', 'enableStandby')
        self.standbyTimeoutSeconds = config.getint('Switches', 'standbyTimeoutSeconds')
        
        self.standby = False
    
    def lockLpack(self):
        while not self.lpack.lock():
            print 'locking...'
            time.sleep(1)
            
    def unlockLpack(self):
        while not self.lpack.unlock():
            print 'locking...'
            time.sleep(1)

    def InitializeGrabbers(self):   
        frameLock = threading.Lock()
        if self.serverType == PRISMATIK:
            ffmpeg_bin = self.scriptDir + r'/ffmpeg.exe'
        else:
            ffmpeg_bin = sys.path[-1]+r'/ffmpeg.exe'
        self.capture = captureInput.captureInput(self.videoDevice, self.videoDeviceName, self.videoX, self.videoY, self.videoFps, self.videoRenderX, self.videoRenderY, frameLock, ffmpeg_bin)
        
        if self.useFfmpeg:
            self.captureThread = threading.Thread(target=self.capture.captureFfmpeg)
        else:
            self.captureThread = threading.Thread(target=self.capture.captureOpenCv)
        self.captureThread.daemon = True
        self.captureThread.start()
        
            
        self.lastFrame = numpy.uint8([[[]]])

        cropWidth = self.videoRenderX-(self.cropLeft+self.cropRight)
        cropHeight = self.videoRenderY-(self.cropTop+self.cropBottom)


        self.xRatio = float(cropWidth)/float(self.screenX)
        self.yRatio = float(cropHeight)/float(self.screenY)

        self.grabbers=[]

        if self.serverType == PRISMATIK:
            self.grabbers = self.prismatikGrabbers()
        else:
            self.grabbers = self.ambiboxGrabbers()
            
        self.signal = True
        self.noSignalFrames = int(0)
        self.standby = False
        return True
        
    def prismatikGrabbers(self):
        retGrabbers=[]
        leds = self.lpack.getLeds();
        for led in leds:  
            if led.isspace():
              continue
            ledDims = led[2:].split(',')
            ledIndex = int(led.split('-')[0])
            left = int(float(ledDims[0])*self.xRatio)
            top = int(float(ledDims[1])*self.yRatio)
            newLedZone = ledZone(ledIndex+1, left, left+int(float(ledDims[2])*self.xRatio), top, top+int(float(ledDims[3])*self.yRatio))
            retGrabbers.append(newLedZone)
        return retGrabbers

    def ambiboxGrabbers(self):
        retGrabbers=[]
        currentProfile = self.lpack.getProfile()
        ledCount = self.lpack.getCountLeds()
        reg = ConnectRegistry(None, HKEY_CURRENT_USER)
        currentProfile = currentProfile.strip()
        key = OpenKey(reg, r'Software\Server IR\Backlight\Profiles\%s' % currentProfile)
        for i in range(0, int(ledCount)):
            zBottom = QueryValueEx(key, 'Zone_Bottom_%s' % str(i))
            zLeft = QueryValueEx(key, 'Zone_Left_%s' % str(i))
            zRight = QueryValueEx(key, 'Zone_Right_%s' % str(i))
            zTop = QueryValueEx(key, 'Zone_Top_%s' % str(i))
            newLedZone = ledZone(i+1, int(float(zLeft[0])*self.xRatio), int(float(zRight[0])*self.xRatio), int(float(zTop[0])*self.yRatio), int(float(zBottom[0])*self.yRatio))
            #print [newLedZone.ledIndex, newLedZone.left, newLedZone.right, newLedZone.top, newLedZone.bottom]
            retGrabbers.append(newLedZone)
        return retGrabbers
        
    def ConnectToLightpack(self):
        try:
            self.lpack.connect()
            return True
        except: return False

    def newSignal(self, frame):
        newFrame = False
        if self.lastFrame is None or len(self.lastFrame) == 1 or frame is None or len(frame) == 1:
            if self.lastFrame is None and frame is None:
                return False
            self.lastFrame = frame
            return True
        
        newFrame = not numpy.allclose(frame, self.lastFrame)
        self.lastFrame = frame
        return newFrame

    def startGrabbing(self):
        
        if not self.ConnectToLightpack():
            print "Unable to connect to AmbiBox!"
            return
            
        if not self.InitializeGrabbers():
            print "Unable to set up grabbers"
            return

        if self.videoFps == 0:
            self.videoFps = 30
            
        loopThrottle = 1.0/float(self.videoFps)
        
        standbyCheckInterval = 5
        loopCounter = 0
        standbyCheckThreshold = standbyCheckInterval*self.videoFps
        noSignalThreshold = int(float(self.standbyTimeoutSeconds) / float(standbyCheckInterval))
        
        cropWidth = self.videoRenderX-(self.cropLeft+self.cropRight)
        cropHeight = self.videoRenderY-(self.cropTop+self.cropBottom)
        
        while self.capture.getFrame() is None: #wait for capture to start
            print 'waiting for first frame'
            time.sleep(1)
            continue
            
        self.lockLpack()
        
        while True:                    
            frame = self.capture.getFrame()
            
            if frame is None: #wait for capture to start
                print 'waiting for first frame'
                time.sleep(1)
                continue
                
            startTime = time.time()
            loopCounter += 1
            
            if loopCounter > standbyCheckThreshold:
                if not self.newSignal(frame):
                    self.noSignalFrames += 1
                else:
                    self.noSignalFrames = 0
                loopCounter = 0
            
            #Sleep until lights are on
            currentStatus = self.lpack.getStatus()
            currentStatus = currentStatus.strip()            
            #enter standby loop
            if (self.enableStandby and self.noSignalFrames >= noSignalThreshold) or currentStatus != "on":
                self.standby = True
                print 'standing by'
                self.lpack.unlock()

                while True:
                    time.sleep(5)
                    currentStatus = self.lpack.getStatus()
                    currentStatus = currentStatus.strip()
                    if self.newSignal(self.capture.getFrame()) and currentStatus == "on":
                        print 'waking back up'
                        self.noSignalFrames = 0
                        self.lockLpack()
                        self.standby = False
                        break
              
            cropFrame = frame[self.cropTop:(self.videoRenderY-self.cropBottom), self.cropLeft:(self.videoRenderX-self.cropRight)]
            
            colorUpdate = []
            for box in self.grabbers:
              roi = cropFrame[box.top:box.bottom, box.left:box.right]
              if self.labColorspace:
                roi = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
                meanLabColor = cv2.mean(roi)
                labColorInts = numpy.uint8([[[meanLabColor[0],meanLabColor[1],meanLabColor[2]]]])
                meanColor = cv2.cvtColor(labColorInts, cv2.COLOR_LAB2BGR)
                meanColor = meanColor[0][0]
              else:
                meanColor = cv2.mean(roi)
              #if self.serverType == PRISMATIK:
              #  self.lpack.setColor(box.ledIndex, int(meanColor[2]), int(meanColor[1]), int(meanColor[0]))
              #else:
              colorUpdate.append((box.ledIndex, [int(meanColor[2]), int(meanColor[1]), int(meanColor[0])]))
            
            #if self.serverType == AMBIBOX:
            self.lpack.updateColors(colorUpdate)

            endTime = time.time()-startTime
            if endTime < loopThrottle:
              time.sleep(loopThrottle-endTime)
        
        
    def __del__(self):
        self.capture.stopCapture()
        self.lpack.unlock()
        self.lpack.disconnect()

class ledZone:
    def __init__(self, _ledIndex, _left, _right, _top, _bottom):
        self.ledIndex = _ledIndex
        self.left = _left
        self.right = _right
        self.top = _top
        self.bottom = _bottom
        
directLight = DirectLight()
directLight.startGrabbing()