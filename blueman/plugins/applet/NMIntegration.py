# Copyright (C) 2008 Valmantas Paliksa <walmis at balticum-tv dot lt>
# Copyright (C) 2008 Tadas Dailyda <tadas at dailyda dot com>
#
# Licensed under the GNU General Public License Version 3
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
from blueman.Functions import *
from blueman.plugins.AppletPlugin import AppletPlugin
from blueman.main.PolicyKitAuth import PolicyKitAuth
from blueman.main.Mechanism import Mechanism
from blueman.main.Config import Config
from blueman.gui.Notification import Notification
from blueman.Sdp import *

from blueman.main.SignalTracker import SignalTracker

import blueman.bluez as Bluez

import gobject
import gtk

class NMIntegration(AppletPlugin):
	__description__ = _("Makes DUN/PAN connections available for NetworkManager 0.7")
	__icon__ = "modem"
	__depends__ = ["DBusService"]
	__conflicts__ = ["PPPSupport"]
	__author__ = "Walmis"
	__priority__ = 1
	
	def on_load(self, applet):
		pass
		
	def on_unload(self):
		pass

	#in: bluez_device_path, rfcomm_device
	#@dbus.service.method(dbus_interface='org.blueman.Applet', in_signature="ss", out_signature="")
	def RegisterModem(self, device_path, rfcomm_device):
		a = PolicyKitAuth()
		authorized = a.is_authorized("org.blueman.hal.manager")
		if not authorized:
			authorized = a.obtain_authorization(False, "org.blueman.hal.manager")
	
		if authorized:
			dev = Bluez.Device(device_path)
			props = dev.GetProperties()
		
			m = Mechanism()

			def reply():
				dprint("Registered modem")
				
			def err(excp):
				d = gtk.MessageDialog(None, type=gtk.MESSAGE_WARNING)
				d.props.icon_name = "blueman"
				d.props.text = _("CDMA or GSM not supported")
				d.props.secondary_text = _("The device %s does not appear to support GSM/CDMA.\nThis connection will not work.") % props["Alias"]

				d.add_button(gtk.STOCK_OK, gtk.RESPONSE_NO)
				resp = d.run()
				d.destroy()

			m.HalRegisterModemPort(rfcomm_device, props["Address"], reply_handler=reply, error_handler=err)

			
		
	#in: bluez_device_path, rfcomm_device
	#@dbus.service.method(dbus_interface='org.blueman.Applet', in_signature="s", out_signature="")
	def UnregisterModem(self, device):
		a = PolicyKitAuth()
		authorized = a.is_authorized("org.blueman.hal.manager")
		if not authorized:
			authorized = a.obtain_authorization(False, "org.blueman.hal.manager")
		
		if authorized:
			m = Mechanism()
			m.HalUnregisterModemPortDev(device)
			
		dprint("Unregistered modem")
		
	def on_rfcomm_connected(self, device, port, uuid):
		signals = SignalTracker()
		def modem_added(mon, udi, address):
			if device.Address == address:
				dprint(udi)
				device.udi = udi
			
		def modem_removed(mon, udi):
			if device.udi == udi:
				dprint(udi)
				signals.DisconnectAll()
			
		def disconnected(mon, udi):
			device.Services["serial"].Disconnect(port)
			self.UnregisterModem(port)
		
		def device_propery_changed(key, value):
			if key == "Connected" and not value:
				self.UnregisterModem(port)
			
	
		uuid16 = uuid128_to_uuid16(uuid)
		if uuid16 == DIALUP_NET_SVCLASS_ID:
			try:
				signals.Handle(self.Applet.Plugins.NMMonitor, "modem-added", modem_added)
				signals.Handle(self.Applet.Plugins.NMMonitor, "modem-removed", modem_removed)
				signals.Handle(self.Applet.Plugins.NMMonitor, "disconnected", disconnected)
			except NameError:
				pass
				
			signals.Handle("bluez", device.Device, device_propery_changed, "PropertyChanged")	
			self.RegisterModem(device.get_object_path(), port)
		
	def rfcomm_connect_handler(self, device, uuid, reply_handler, error_handler):
		uuid16 = uuid128_to_uuid16(uuid)
		if uuid16 == DIALUP_NET_SVCLASS_ID:
			device.Services["serial"].Connect(uuid, reply_handler=reply_handler, error_handler=error_handler)
			return True
		else:
			return False	
		
		
	def on_rfcomm_disconnect(self, port):
		self.UnregisterModem(port)