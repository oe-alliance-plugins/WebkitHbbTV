from __future__ import print_function
from os import system
from subprocess import call
from time import localtime, strftime

from enigma import eRCInput, fbClass, gMainDC, getDesktop

from Tools.Directories import fileExists


g_main = None
g_browser = None
g_youtubetv_cfg = None
g_service = None
g_channel_info = None
g_position = None
displayAccess = None

need_restart = False

APPROOT = "/usr/bin"
APP_ENV = "MOZ_PLUGIN_PATH=/usr/lib/mozilla/plugins"
APP_RUN = "browser"
APP_INDEX = "/home/root/none.html"

PLUGINROOT = "/usr/lib/enigma2/python/Plugins/Extensions/WebkitHbbTV"
MANUALROOT = "/usr/local/manual"
DFBRC = "/etc/directfbrc"

SOCKETFILE = None
CONTROLFILE = None


def getPosition():
	if not fileExists("/proc/stb/fb/dst_left"):
		return None
	try:
		file = open("/proc/stb/fb/dst_left", "r")
		dst_left = int(file.read().strip(), 16)
		file.close()
		file = open("/proc/stb/fb/dst_width", "r")
		dst_width = int(file.read().strip(), 16)
		file.close()
		file = open("/proc/stb/fb/dst_top", "r")
		dst_top = int(file.read().strip(), 16)
		file.close()
		file = open("/proc/stb/fb/dst_height", "r")
		dst_height = int(file.read().strip(), 16)
		file.close()
	except Exception as Err:
		ERR(Err)
		return None
	return (dst_left, dst_width, dst_top, dst_height)


def setPosition(params):
	if params is None:
		return
	if params[0] + params[1] > 720 or params[2] + params[3] > 576:
		return
	else:
		try:
			file = open("/proc/stb/fb/dst_left", "w")
			file.write('%X' % params[0])
			file.close()
			file = open("/proc/stb/fb/dst_width", "w")
			file.write('%X' % params[1])
			file.close()
			file = open("/proc/stb/fb/dst_top", "w")
			file.write('%X' % params[2])
			file.close()
			file = open("/proc/stb/fb/dst_height", "w")
			file.write('%X' % params[3])
			file.close()
		except Exception as Err:
			ERR(Err)
			return


def setBrowserPlane(visible):
	if not fileExists("/usr/bin/config"):
		return True
	planes = (("DirectFB", "on"), ("1", "off")) if visible else (("1", "on"), ("DirectFB", "off"))
	try:
		results = [call(("/usr/bin/config", "-c", plane, "-visible", state)) for plane, state in planes]
		return not any(results)
	except OSError as error:
		print(f"[WebkitHbbTV] Unable to switch display planes: {error}")
		return False


def osd_lock(owner=None):
	global displayAccess
	if displayAccess is not None:
		return displayAccess[0] is owner
	mainDC = gMainDC.getInstance()
	framebuffer = fbClass.getInstance()
	remote = eRCInput.getInstance()
	canSuspend = hasattr(mainDC, "suspendGraphics") and hasattr(mainDC, "resumeGraphics") and hasattr(mainDC, "isGraphicsSuspended")
	if remote is None or remote.islocked() or (canSuspend and mainDC.isGraphicsSuspended()):
		return False
	if framebuffer is None and not canSuspend:
		return False
	position = getPosition()
	if framebuffer is not None and framebuffer.lock() < 0:
		return False
	# An EGL renderer can own an OSD plane even when there is no fbClass instance.
	if canSuspend and not mainDC.suspendGraphics():
		if framebuffer is not None:
			try:
				framebuffer.unlock(False)
			except TypeError:  # Older bindings only expose unlock().
				framebuffer.unlock()
		return False
	remote.lock()
	displayAccess = (owner, framebuffer, mainDC, remote, canSuspend, position)
	if not setBrowserPlane(True):
		osd_unlock(owner)
		return False
	return True


def osd_unlock(owner=None):
	global displayAccess
	if displayAccess is None or displayAccess[0] is not owner:
		return False
	owner, framebuffer, mainDC, remote, suspended, position = displayAccess
	displayAccess = None
	try:
		if not setBrowserPlane(False):
			print("[WebkitHbbTV] Unable to restore Enigma2 display plane.")
		desktop = getDesktop(0)
		if not suspended and mainDC is not None:
			size = desktop.size()
			mainDC.setResolution(size.width(), size.height())
		if framebuffer is not None:
			framebuffer.unlock()
		# The framebuffer renderer rebinds its drawing surface after unlock.
		if suspended and not mainDC.resumeGraphics():
			print("[HbbTV] Unable to resume Enigma2 graphics.")
			return False
		setPosition(position)
		desktop.paint()
	finally:
		remote.unlock()
	return True


def set_bgcolor(val):
	DEBUG("val = %s from %s" % (val, DFBRC))
	system('sed \'s/bg-color=[0,f]*/bg-color=%s/\' %s > /tmp/tmprc' % (val, DFBRC))
	system('mv /tmp/tmprc %s && rm -f /tmp/tmprc' % DFBRC)


# for debug True
# g_debug = True
g_debug = False


def LogEntry(mode, string):
	if g_debug:
		print(strftime("%x %X", localtime()), "%5s [%12s]" % (mode, "Plugin"), string)
	elif mode != "DEBUG":
		print("[browser] %s" % string)


def DEBUG(string):
	if g_debug:
		LogEntry("DEBUG", string)


def LOG(string):
	if g_debug:
		LogEntry("LOG", string)


def WARN(string):
	if g_debug:
		LogEntry("WARN", string)


def ERR(string):
	if g_debug:
		LogEntry("ERROR", string)
