from __future__ import print_function
import time
import pychromecast
import inspect

import gobject
import dbus
import dbus.service
import dbus.mainloop.glib

class DBusObjectWithProperties(dbus.service.Object):
    IFACE = {}
    def __init__(self, bus, path):
        dbus.service.Object.__init__(self, bus, path)

    @dbus.service.method("org.freedesktop.DBus.Properties", in_signature='ss', out_signature='v')
    def Get(self, interface_name, property_name):
        if interface_name == DBusObjectWithProperties.IFACE:
            return getattr(self)[property_name]
        else:
            raise dbus.exceptions.DBusException(
                DBusObjectWithProperties.IFACE,
                'The Foo object does not implement the %s interface' % interface_name)

    @dbus.service.method("org.freedesktop.DBus.Properties", in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface_name):
        if not interface_name:
            interface_name = self.IFACE

        if not interface_name in self.IFACE:
            error = 'The %s object does not implement the %s interface. Only \'%s\'' % (type(self).__name__, interface_name, ", ".join(self.IFACE))
            raise dbus.exceptions.DBusException(
                DBusObjectWithProperties.IFACE,
                error)
            return {}

        properties = inspect.getmembers(self.__class__, lambda prop: isinstance(prop, property))
        ret = {}
        for (name, value) in properties:
            if name[0].isupper():
                ret[name] = value.__get__(self)
        #print("trololo", ret)
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
    IFACE = {"org.mpris.MediaPlayer2", "org.mpris.MediaPlayer2.Player"}

    def __init__(self, bus, path, device):
        DBusObjectWithProperties.__init__(self, bus, path)
        print("created device", device.name)
        self.device = device

    # org.mpris.MediaPlayer2
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

    # org.mpris.MediaPlayer2.Player
    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature='', out_signature='')
    def Next(self):
        pass

    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature='', out_signature='')
    def Previous(self):
        pass

    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature='', out_signature='')
    def Pause(self):
        pass

    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature='', out_signature='')
    def PlayPause(self):
        pass

    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature='', out_signature='')
    def Stop(self):
        pass

    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature='', out_signature='')
    def Play(self):
        pass

    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature='x', out_signature='')
    def Seek(self, offset):
        pass

    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature='ox', out_signature='')
    def SetPosition(self, trackId, position):
        pass

    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature='s', out_signature='')
    def OpenUri(self, uri):
        pass

    @property
    def PlaybackStatus(self):
        return dbus.String("Playing")

    @property
    def Rate(self):
        return dbus.Double(1.0)

    @property
    def MinimumRate(self):
        return dbus.Double(1.0)

    @property
    def MaximumRate(self):
        return dbus.Double(1.0)

    @property
    def Shuffle(self):
        return dbus.Boolean(False)

    @property
    def Metadata(self):
        return dbus.Dictionary((), signature='sv')

    @property
    def Volume(self):
        return dbus.Double(1.0)

    @property
    def PlaybackStatus(self):
        return dbus.String("Playing")

    @property
    def CanGoNext(self):
        return dbus.Boolean(False)

    @property
    def CanGoPrevious(self):
        return dbus.Boolean(False)

    @property
    def CanPlay(self):
        return dbus.Boolean(False)

    @property
    def CanPause(self):
        return dbus.Boolean(False)

    @property
    def CanSeek(self):
        return dbus.Boolean(False)

    @property
    def CanControl(self):
        return dbus.Boolean(False)

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    session_bus = dbus.SessionBus()
    devices = pychromecast.get_chromecasts_as_dict()
    deviceDBusObjects = []
    for (name, cast) in devices.items():
        name = dbus.service.BusName("org.mpris.MediaPlayer2.chromecast-" + name, session_bus)
        deviceDBusObjects.append(MprisChromecastObject(session_bus, '/org/mpris/MediaPlayer2', cast))

    mainloop = gobject.MainLoop()
    mainloop.run()
