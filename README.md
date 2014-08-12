#DirectLight

##Description
DirectLight is an AmbiBox and Prismatik plugin that allows a DirectShow capture device to be used as a grabbing source.
This allows external video devices to take advantage of backlighting.

## Version 0.1

##Dependencies
* Python 2.7 (32 bit)
* NumPy
* OpenCV (2.4.9 build included in this repository)
* FFmpeg (optional, required if using FFmpeg capture instead of OpenCV)
* AmbiBox (tested on 2.1.5) or Prismatik (tested on 5.11.1)
* A DirectShow compatible capture device

##Installation
* Install Python 2.7 and NumPy
* Download the ZIP from the repository
* Unzip to a new local folder
* If using Prismatik:
  * Enable the API
    * Enable 'Expert mode' under 'Profiles'
    * Check 'Enable server' under 'Experimental'
  * Place the unzipped folder in the Prismatik plugins directory (e.g. 'C:\Users\owenb321\Prismatik\Plugins\DirectLight')
  * Open DirectLight.ini in the DirectLight folder and set 'serverType' to 'prismatik'
  * Refresh the plugin list in Prismatik
* If using AmbiBox:
  * Open DirectLight.ini in the DirectLight folder and set 'serverType' to 'ambibox'
  * Run AmbiBox as administrator (required to update plugin settings)
  * Click the 'Intelligent backlight display' button and enable the API server under the 'Additional settings' tab
  * Click the 'Plugins' button, select 'PythonScriptManager' and click 'Show settings'
  * Click 'Add Script' in the popup, navigate to the folder you unzipped the plugin to and select 'DirectLight.py'
* If using FFmpeg to open the capture device (may be necessary for some capture devices)
  * Download an FFmpeg.exe build, this was tested with a Zeranoe build from http://ffmpeg.zeranoe.com/builds/
  * Place ffmpeg.exe in the DirectLight folder

##Configuration
Screen grabbing zones must be configured in AmbiBox/Prismatik.

Other settings are configured in the 'DirectLight.ini' file.
* Main
  * These are used by Prismatik to identify the plugin
* Capture
  * 'videoDevice' and 'videoDeviceName' are the DirectShow provided name and number for the capture device. These can be found by running 'ListDevices.py' included in the repository and reading the devices.txt file it outputs.
  * 'videoWidth'/'videoHeight' sets the resolution to request from the capture device. (OpenCV may ignore this setting and default to 640x480 anyway)
  * 'videoFramerate' sets the framerate (FPS) to request from the capture device.
* Render
  * Sets the resolution to process the captured image at.  May improve performance if set lower than capture resolution (untested).
* Cropping
  * Sets the number of pixels to crop from each side to remove unwanted borders that can by caused by analog capture devices
* Display
  * Sets the resolution of the display Prismatik/AmbiBox is set to capture. This is required to scale the grabber zones to the DirectShow source properly.
* Lightpack
  * 'host' - Address of the API server. '127.0.0.1' is the local machine.
  * 'port' - API server port number. '3636' is the default.
* Switches
  * 'serverType' - selects which backlight software being used. Can be set to 'prismatik' or 'ambibox'
  * 'useFfmpeg' - '1' or '0'. If enabled, uses FFmpeg to open capture device
  * 'labColorspace' - '1' or '0'. If enabled, uses the L*a*b* colorspace to provide more accurate color averaging, but may increase processing time
  * 'enableStandby' - '1' or '0'. If enabled, checks if the image has changed periodically and unlocks the API if there has been no change. May not work properly with an analog capture device.
  * 'standbyTimeoutSeconds' - Number of seconds before entering standby (if enabled)

##Hardware
A DirectShow compatible capture device is required.
I've tested this with a Somagic version EasyCap (aka SM-USB 007 or SMI Grabber Device).
My set up was an A/V receiver hooked up to an HDMI splitter, then run through an HDMI to composite adapter, and finally the EasyCap.
This worked with OpenCV capturing, but had a slightly noticeable delay in backlighting.

My current set up is using an AVerMedia ExtremeCap U3 which has an HDMI input.
This required using FFmpeg to capture since OpenCV was unable to set the capture resolution properly (capturing at 640x480 returns a garbled screen with a 1080p HDMI input).
I see no noticeable delay when using this card.