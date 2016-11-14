from __future__ import print_function
import time
import pychromecast
import inspect

import gobject
import dbus
import dbus.service
import dbus.mainloop.glib

class DBusObjectWithProperties(dbus.service.Object):
    IFACE = ""
    def __init__(self, bus, path):
        dbus.service.Object.__init__(self, bus, path)

    @dbus.service.method("org.freedesktop.DBus.Properties", in_signature='ss', out_signature='v')
    def Get(self, interface_name, property_name):
        if interface_name == DBusObjectWithProperties.IFACE:
            return getattr(self)[property_name]
        else:
            raise dbus.exceptions.DBusException(
                'com.example.UnknownInterface',
                'The Foo object does not implement the %s interface' % interface_name)

    @dbus.service.method("org.freedesktop.DBus.Properties", in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface_name):
        if not interface_name:
            interface_name = self.IFACE

        if interface_name != self.IFACE:
            raise dbus.exceptions.DBusException(
                'com.example.UnknownInterface',
                'The Foo object does not implement the %s interface' % interface_name)
        properties = inspect.getmembers(self.__class__, lambda prop: isinstance(prop, property))
        ret = {}
        for (name, value) in properties:
            if name[0].isupper():
                ret[name] = value.__get__(self)
        print("trololo", ret)
        return ret

    @dbus.service.method("org.freedesktop.DBus.Properties", in_signature='ssv')
    def Set(self, interface_name, property_name, new_value):
        # validate the property name and value, update internal state…
        self.PropertiesChanged(interface_name, { property_name: new_value }, [])

    @dbus.service.signal("org.freedesktop.DBus.Properties", signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties, invalidated_properties):
        pass

# implements https://specifications.freedesktop.org/mpris-spec/latest/
class MprisChromecastObject(DBusObjectWithProperties):
    IFACE = "org.mpris.MediaPlayer2"

    def __init__(self, bus, path, device):
        DBusObjectWithProperties.__init__(self, bus, path)
        self.device = device

    @dbus.service.method("org.mpris.MediaPlayer2", in_signature='', out_signature='')
    def Raise(self):
        pass

    @dbus.service.method("org.mpris.MediaPlayer2", in_signature='', out_signature='')
    def Quit(self):
        pass

    @property
    def CanQuit(self):
        return dbus.Boolean(False)

    @property
    def CanSetFullscreen(self):
        return dbus.Boolean(False)

    @property
    def CanRaise(self):
        return dbus.Boolean(False)

    @property
    def HasTrackList(self):
        return dbus.Boolean(False)

    @property
    def Identity(self):
        #return dbus.String(self.device.uuid)
        return dbus.String(self.device.name)

    @property
    def SupportedUriSchemes(self):
        return dbus.Array([], signature='s')

    @property
    def SupportedMimeTypes(self):
        return dbus.Array([], signature='s')

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    session_bus = dbus.SessionBus()
    devices = pychromecast.get_chromecasts_as_dict()
    deviceDBusObjects = []
    for (name, cast) in devices.items():
        name = dbus.service.BusName("org.mpris.MediaPlayer2.chromecast-" + name, session_bus)
        deviceDBusObjects.append(MprisChromecastObject(session_bus, '/org/chromecast/MediaPlayer2', cast))

    mainloop = gobject.MainLoop()
    mainloop.run()
