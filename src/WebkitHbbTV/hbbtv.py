from __future__ import absolute_import
from glob import iglob
from os import X_OK, access
from os.path import realpath
from subprocess import call

from enigma import eTimer

from Screens.Screen import Screen

from . import vbcfg
from .__init__ import _


class HbbTVWindow(Screen):
	skin = """
		<screen name="HbbTVWindow" position="0,0" size="1280,720" backgroundColor="transparent" flags="wfNoBorder" title="HbbTV Plugin">
		</screen>
		"""

	def __init__(self, session, url=None, app_info=None):
		Screen.__init__(self, session)
		self._url = url
		self._info = app_info
		self.browserStarted = False
		self.browserPath = realpath("/usr/bin/browser")
		self.browserProcess = None
		self.browserTimer = eTimer()
		self.browserTimer.callback.append(self.checkBrowser)
		self._close_timer = eTimer()
		self._close_timer.callback.append(self.stop_hbbtv_application)
		self.onLayoutFinish.append(self.start_hbbtv_application)
		self.onClose.append(self.releaseBrowser)

	def _cb_set_title(self, title=None):
		vbcfg.LOG("pate title: %s" % title)
		if title is None:
			return
		self.setTitle(title)

	def _cb_close_window(self):
		self._close_timer.start(1000, True)

	def start_hbbtv_application(self):
		if self.browserStarted:
			return
		info = self._info or {}
		loadAit = info.get("control") == 1 and vbcfg.g_channel_info is not None
		url = info.get("url") if loadAit else self._url or info.get("url")
		if not url or not access("/usr/bin/browser", X_OK):
			print("[HbbTV] No application URL or browser executable.")
			self.close()
			return
		if not vbcfg.osd_lock(self):
			print("[HbbTV] Display or remote control unavailable; browser not started.")
			self.close()
			return
		self.browserStarted = True
		handler = vbcfg.g_main.vbhandler
		handler.onSetTitleCB.append(self._cb_set_title)
		handler.onCloseCB.append(self._cb_close_window)
		handler.soft_volume = -1
		self.setTitle(_("HbbTV Plugin"))
		try:
			# The vendor launcher backgrounds the browser and normally exits with status 1.
			if call(("/usr/bin/run-webkit.sh", "restart", url)) not in (0, 1):
				self.close()
				return
			self.browserTimer.startLongTimer(5)
		except (OSError, TypeError, ValueError) as error:
			print(f"[HbbTV] Browser launch failed: {error}")
			self.close()

	def checkBrowser(self):
		# The launcher forks: an early browser exit may never send CONTROL_EXIT.
		if not self.browserProcess or realpath(self.browserProcess) != self.browserPath:
			self.browserProcess = next((path for path in iglob("/proc/[0-9]*/exe") if realpath(path) == self.browserPath), None)
		if self.browserProcess:
			self.browserTimer.startLongTimer(5)
		else:
			print("[HbbTV] Browser process exited without a close notification.")
			self.close()

	def stop_hbbtv_application(self):
		self.close()

	def releaseBrowser(self):
		self.browserTimer.stop()
		self._close_timer.stop()
		if not self.browserStarted:
			return
		self.browserStarted = False
		handler = vbcfg.g_main.vbhandler
		if self._cb_set_title in handler.onSetTitleCB:
			handler.onSetTitleCB.remove(self._cb_set_title)
		if self._cb_close_window in handler.onCloseCB:
			handler.onCloseCB.remove(self._cb_close_window)
		vbcfg.osd_unlock(self)
		vbcfg.set_bgcolor("0")
