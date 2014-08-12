import subprocess as sp
import cv2
import threading
import numpy
import time

class captureInput:
    
    def __init__(self, deviceNum, deviceName, captureX, captureY, fps, renderX, renderY, frameLock, ffmpegPath='ffmpeg.exe'):
        self.deviceNum = deviceNum
        self.deviceName = deviceName
        self.captureX = captureX
        self.captureY = captureY
        self.fps = fps
        self.renderX = renderX
        self.renderY = renderY
        self.stopFlag = False
        
        self.cap = None
        self.pipe = None
        self.ffmpegPath = ffmpegPath
        
        self.frameLock = frameLock
        self.currentFrame = None
        
    def setupFfmpeg(self):
        inputDevice = 'video=' + self.deviceName
        inputRes = str(self.captureX) + 'x' + str(self.captureY)
        outputRes = 'scale='+str(self.renderX)+':'+str(self.renderY)
        command = [ self.ffmpegPath ]
        if self.captureX != 0 and self.captureY != 0:
            command.extend(['-s', inputRes])
        command.extend( [ #'-loglevel', 'panic',
            '-f', 'dshow',
            '-i', inputDevice ])
        if self.fps != 0:
            command.extend(['-r', str(self.fps)])
        command.extend([
            '-f', 'image2pipe',
            '-vf', str(outputRes),
            '-pix_fmt', 'bgr24',
            '-vcodec', 'rawvideo',
            '-acodec', 'none',
            '-'])
        print command
        self.pipe = sp.Popen(command, stdout = sp.PIPE, bufsize=-1)
    
    def captureFfmpeg(self):
        self.setupFfmpeg()
        self.stopFlag = False
        while True:
            if self.pipe.poll() is not None:
                self.setupFfmpeg()
            raw_image = self.pipe.stdout.read(self.renderX*self.renderY*3)
            if self.stopFlag:
                break
            # transform the byte read into a numpy array
            frame =  numpy.fromstring(raw_image, dtype='uint8')
            frame = frame.reshape((self.renderY,self.renderX,3))
            # throw away the data in the pipe's buffer.
            self.pipe.stdout.flush()
            self.setFrame(frame)
            
    def captureOpenCv(self):
        self.stopFlag = False
        self.cap = cv2.VideoCapture(0)

        self.cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, self.captureX)
        self.cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, self.captureY)
        while True:
            ret, frame = self.cap.read()
            cv2.waitKey(1)
            if self.stopFlag:
                break
            if not ret:
                continue
            if self.captureX != self.renderX or self.captureY != self.renderY:
                frame = cv2.resize(frame, (self.renderX, self.renderY))
            self.setFrame(frame)
    
    def setFrame(self, frame):
        self.frameLock.acquire()
        self.currentFrame = frame
        self.frameLock.release()
        
    def getFrame(self):
        self.frameLock.acquire()
        returnFrame = self.currentFrame
        self.frameLock.release()
        return returnFrame
        
    def stopCapture(self):
        self.stopFlag = True
        if self.pipe is not None:
            self.pipe.kill()
            self.pipe.wait()
        if self.cap is not None:
            self.cap.release()
            
    def __del__(self):
        self.stopCapture()
        