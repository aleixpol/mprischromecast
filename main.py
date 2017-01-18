from __future__ import print_function
import time
import pychromecast
import inspect
import logging

import gobject
import dbus
import dbus.service
import dbus.mainloop.glib
import glib

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
                try:
                    ret[name] = value(self)
                except Exception as exception:
                    logging.exception(exception)

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
        # validate the property name and value, update internal state
        self.PropertiesChanged(interface_name, { property_name: new_value }, [])

    @dbus.service.signal("org.freedesktop.DBus.Properties", signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties, invalidated_properties):
        print("PropertiesChanged", interface_name, changed_properties.keys())
        pass # TODO figure out which actually changed

    def emitPropertiesChanged(self, interface_name, changed_properties, invalidated_properties):
        self.PropertiesChanged(dbus.String(interface_name), dbus.Dictionary(changed_properties, 'sv'), dbus.Array(invalidated_properties, 'as'))

# implements https://specifications.freedesktop.org/mpris-spec/latest/
class MprisChromecastObject(DBusObjectWithProperties):
    IFACE = "org.mpris.MediaPlayer2"

    def __init__(self, bus, path, cast):
        DBusObjectWithProperties.__init__(self, bus, path)
        self.cast = cast
        self.cast.media_controller.register_status_listener(self)
        print("created device!", cast.name)

        glib.timeout_add_seconds(1, self.iterateCastLoop)

    def iterateCastLoop(self):
        glib.timeout_add_seconds(1, self.iterateCastLoop)
        self.cast.socket_client.run_once()

    def new_media_status(self, newstatus):
        print("statusChanged", newstatus)
        self.emitPropertiesChanged("org.mpris.MediaPlayer2.Player", self.GetAll("org.mpris.MediaPlayer2.Player"), [])

    @DBusProperty("org.mpris.MediaPlayer2")
    def Identity(self):
        #return dbus.String(self.cast.uuid)
        return dbus.String(self.cast.name)

    @dbus.service.method("org.mpris.MediaPlayer2", in_signature='', out_signature='')
    def Quit(self):
        self.cast.quit_app()

    @DBusProperty("org.mpris.MediaPlayer2")
    def CanQuit(self):
        return dbus.Boolean(True)

    @DBusProperty("org.mpris.MediaPlayer2")
    def SupportedUriSchemes(self):
        return dbus.Array(["http", "https"], signature='s')

    @DBusProperty("org.mpris.MediaPlayer2")
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
        if mc.status.player_state == pychromecast.controllers.media.MEDIA_PLAYER_STATE_PLAYING:
            return dbus.String("Playing")
        elif mc.status.player_state == pychromecast.controllers.media.MEDIA_PLAYER_STATE_PAUSED:
            return dbus.String("Paused")
        else:
            return dbus.String("Stopped")

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def Metadata(self):
        #see https://www.freedesktop.org/wiki/Specifications/mpris-spec/metadata/

        mc = self.cast.media_controller
        metadata = {
            "mpris:length": mc.status.duration,
            "mpris:artUrl": mc.status.images[0] if len(mc.status.images)>0 else "",

            "xesam:album": mc.status.album_name,
            "xesam:albumArtist": mc.status.album_artist,
            "xesam:artist": mc.status.artist,
            "xesam:comment": mc.status.series_title,
            "xesam:trackNumber": mc.status.track,
            "xesam:title": mc.status.title
        }
        return dbus.Dictionary({ a:b for (a,b) in metadata.items() if b }, signature='sv')

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def Volume(self):
        mc = self.cast.media_controller
        return dbus.Double(mc.status.volume_level)

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def CanGoNext(self):
        mc = self.cast.media_controller
        return dbus.Boolean(mc.status.supports_skip_forward)

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def CanGoPrevious(self):
        mc = self.cast.media_controller
        return dbus.Boolean(mc.status.supports_skip_backward)

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def CanPlay(self):
        mc = self.cast.media_controller
        return dbus.Boolean(mc.status.supports_pause)

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def CanPause(self):
        mc = self.cast.media_controller
        return dbus.Boolean(mc.status.supports_pause)

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def CanSeek(self):
        mc = self.cast.media_controller
        return dbus.Boolean(mc.status.supports_seek)

#TODO
    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def Shuffle(self):
        return dbus.Boolean(False)

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def CanControl(self):
        return dbus.Boolean(False)

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def Rate(self):
        return dbus.Double(1.0)

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def MinimumRate(self):
        return dbus.Double(1.0)

    @DBusProperty("org.mpris.MediaPlayer2.Player")
    def MaximumRate(self):
        return dbus.Double(1.0)

    @dbus.service.method("org.mpris.MediaPlayer2", in_signature='', out_signature='')
    def Raise(self):
        pass

    @DBusProperty("org.mpris.MediaPlayer2")
    def CanSetFullscreen(self):
        return dbus.Boolean(False)

    @DBusProperty("org.mpris.MediaPlayer2")
    def CanRaise(self):
        return dbus.Boolean(False)

    @DBusProperty("org.mpris.MediaPlayer2")
    def HasTrackList(self):
        return dbus.Boolean(False)

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    session_bus = dbus.SessionBus()
    devices = pychromecast.get_chromecasts()
    deviceDBusObjects = []
    for cast in devices:
        bus = dbus.service.BusName("org.mpris.MediaPlayer2.chromecast-" + cast.name, session_bus)
        deviceDBusObjects.append(MprisChromecastObject(bus, '/org/mpris/MediaPlayer2', cast))

    mainloop = gobject.MainLoop()
    mainloop.run()
