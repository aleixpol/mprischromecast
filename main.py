from __future__ import print_function
import time
import pychromecast
import inspect

import gobject
import dbus
import dbus.service
import dbus.mainloop.glib

def DBusProperty(name):
    def decorate(x):
        x._dbus_property_interface = name
        return x
    return decorate

class DBusObjectWithProperties(dbus.service.Object):
    IFACE = ""
    def __init__(self, bus, path):
        dbus.service.Object.__init__(self, bus, path)

    @dbus.service.method("org.freedesktop.DBus.Properties", in_signature='ss', out_signature='v')
    def Get(self, interface_name, property_name):
        val = getattr(self)[property_name]
        if interface_name == val._dbus_property_interface:
            return val
        else:
            raise dbus.exceptions.DBusException(
                DBusObjectWithProperties.IFACE,
                'The %s object does not implement the %s interface' % (type(self).__name__, interface_name))

    def inspectAttr(self, iface, p):
        ret = getattr(p, "_dbus_property_interface", "") == iface
        return ret

    @dbus.service.method("org.freedesktop.DBus.Properties", in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface_name):
        properties = inspect.getmembers(self.__class__, predicate=lambda p: self.inspectAttr(interface_name, p))
        ret = {}
        for (name, value) in properties:
            if name[0].isupper():
                ret[name] = value(self)

        if not ret:
            error = 'The %s object does not implement the %s interface.' % (type(self).__name__, interface_name)
            raise dbus.exceptions.DBusException(
                self.IFACE,
                error)
            return {}

        #print("trololo", ret)
        return ret

    @dbus.service.method("org.freedesktop.DBus.Properties", in_signature='ssv')
    def Set(self, interface_name, property_name, new_value):
        # validate the property name and value, update internal state…
        self.PropertiesChanged(interface_name, { property_name: new_value }, [])

    @dbus.service.signal("org.freedesktop.DBus.Properties", signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties, invalidated_properties):
        pass # TODO

# implements https://specifications.freedesktop.org/mpris-spec/latest/
class MprisChromecastObject(DBusObjectWithProperties):
    IFACE = "org.mpris.MediaPlayer2"

    def __init__(self, bus, path, cast):
        DBusObjectWithProperties.__init__(self, bus, path)
        print("created device", cast.name)
        self.cast = cast

    # org.mpris.MediaPlayer2
    @dbus.service.method("org.mpris.MediaPlayer2", in_signature='', out_signature='')
    def Raise(self):
        pass

    @dbus.service.method("org.mpris.MediaPlayer2", in_signature='', out_signature='')
    def Quit(self):
        pass

    @DBusProperty("org.mpris.MediaPlayer2")
    def CanQuit(self):
        return dbus.Boolean(False)

    @DBusProperty("org.mpris.MediaPlayer2")
    def CanSetFullscreen(self):
        return dbus.Boolean(False)

    @DBusProperty("org.mpris.MediaPlayer2")
    def CanRaise(self):
        return dbus.Boolean(False)

    @DBusProperty("org.mpris.MediaPlayer2")
    def HasTrackList(self):
        return dbus.Boolean(False)

    @DBusProperty("org.mpris.MediaPlayer2")
    def Identity(self):
        #return dbus.String(self.cast.uuid)
        return dbus.String(self.cast.name)

    @DBusProperty("org.mpris.MediaPlayer2")
    def SupportedUriSchemes(self):
        return dbus.Array([], signature='s')

    @DBusProperty("org.mpris.MediaPlayer2")
    def SupportedMimeTypes(self):
        return dbus.Array([], signature='s')

    # org.mpris.MediaPlayer2.Player
    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature='', out_signature='')
    def Next(self):
        pass

    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature='', out_signature='')
    def Previous(self):
        mc = self.cast.media_controller
        mc.plause()

    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature='', out_signature='')
    def Pause(self):
        mc = self.cast.media_controller
        mc.pause()

    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature='', out_signature='')
    def PlayPause(self):
        mc = self.cast.media_controller
        if mc.player_is_playing:
            mc.pause()
        else:
            mc.play()


    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature='', out_signature='')
    def Stop(self):
        mc = self.cast.media_controller
        mc.stop()

    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature='', out_signature='')
    def Play(self):
        mc = self.cast.media_controller
        mc.play()

    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature='x', out_signature='')
    def Seek(self, offset):
        mc = self.cast.media_controller
        mc.seek(offset)

    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature='ox', out_signature='')
    def SetPosition(self, trackId, position):
        pass

    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature='s', out_signature='')
    def OpenUri(self, uri):
        mc = self.cast.media_controller
        mc.play_media(uri)

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def PlaybackStatus(self):
        mc = self.cast.media_controller
        if mc.player_state == pychromecast.media.MEDIA_PLAYER_STATE_PLAYING:
            return dbus.String("Playing")
        elif mc.player_state == pychromecast.media.MEDIA_PLAYER_STATE_PAUSED:
            return dbus.String("Paused")
        else:
            return dbus.String("Stopped")

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def Shuffle(self):
        console.log("not implemented")
        return dbus.Boolean(False)

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def Metadata(self):
        return dbus.Dictionary((), signature='sv')

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def Volume(self):
        return dbus.Double(self.cast.status.volume_level)

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def PlaybackStatus(self):
        return dbus.String("Playing")

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def CanGoNext(self):
        mc = self.cast.media_controller
        return dbus.Boolean(mc.supports_skip_forward)

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def CanGoPrevious(self):
        mc = self.cast.media_controller
        return dbus.Boolean(mc.supports_skip_backward)

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def CanPlay(self):
        mc = self.cast.media_controller
        return dbus.Boolean(mc.supports_pause)

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def CanPause(self):
        mc = self.cast.media_controller
        return dbus.Boolean(mc.supports_pause)

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def CanSeek(self):
        mc = self.cast.media_controller
        return dbus.Boolean(mc.supports_seek)

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def CanControl(self):
        return dbus.Boolean(False)

#TODO
    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def Rate(self):
        return dbus.Double(1.0)

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def MinimumRate(self):
        return dbus.Double(1.0)

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def MaximumRate(self):
        return dbus.Double(1.0)

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    session_bus = dbus.SessionBus()
    devices = pychromecast.get_chromecasts_as_dict()
    deviceDBusObjects = []
    for (name, cast) in devices.items():
        bus = dbus.service.BusName("org.mpris.MediaPlayer2.chromecast-" + name, session_bus)
        deviceDBusObjects.append(MprisChromecastObject(bus, '/org/mpris/MediaPlayer2', cast))


    mainloop = gobject.MainLoop()
    mainloop.run()
