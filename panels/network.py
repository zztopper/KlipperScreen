import gi
import json
import logging
import os
import re

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango

from ks_includes.screen_panel import ScreenPanel

def create_panel(*args):
    return NetworkPanel(*args)

class NetworkPanel(ScreenPanel):
    networks = {}
    network_list = []
    interface = "wlan0"

    def initialize(self, menu):
        _ = self.lang.gettext
        grid = self._gtk.HomogeneousGrid()
        grid.set_hexpand(True)

        # Get Hostname
        stream = os.popen('hostname -A')
        hostname = stream.read()
        # Get IP Address
        stream = os.popen('hostname -I')
        ip = stream.read()

        # Get active interface
        stream = os.popen("route | grep ^'default' | grep -o '[^ ]*$'")
        active_int = stream.read().strip()
        logging.debug("Active network int: '%s'" % active_int)

        self.labels['networks'] = {}

        self.labels['interface'] = Gtk.Label()
        self.labels['interface'].set_text(" %s: %s" % (_("Interface"), self.interface))
        self.labels['disconnect'] = self._gtk.Button(_("Disconnect"), "color2")


        sbox = Gtk.Box()
        sbox.set_hexpand(True)
        sbox.set_vexpand(False)
        sbox.add(self.labels['interface'])
        #sbox.add(self.labels['disconnect'])


        scroll = Gtk.ScrolledWindow()
        scroll.set_property("overlay-scrolling", False)
        scroll.set_vexpand(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_vexpand(True)

        self.labels['networklist'] = Gtk.Grid()
        self.files = {}

        if len(self._screen.wireless_interfaces) > 0:
            box.pack_start(sbox, False, False, 0)
            box.pack_start(scroll, True, True, 0)

            GLib.idle_add(self.load_networks)
            scroll.add(self.labels['networklist'])
        else:
            self.labels['networkinfo'] = Gtk.Label(
                _("Network Info") + "\n\n%s%s" % (hostname, ip)
            )
            self.labels['networkinfo'].get_style_context().add_class('temperature_entry')
            box.pack_start(self.labels['networkinfo'], False, False, 0)

        self.content.add(box)
        self.labels['main_box'] = box
        self._screen.wifi.add_callback("connected", self.connected_callback)
        self._screen.wifi.add_callback("scan_results", self.scan_callback)

    def load_networks(self):
        networks = self._screen.wifi.get_networks()
        logging.debug("Networks: %s" % json.dumps(networks, indent=2))

        conn_ssid = self._screen.wifi.get_connected_ssid()
        if conn_ssid in networks:
            networks.remove(conn_ssid)
        self.add_network(conn_ssid, False)

        for net in networks:
            self.add_network(net, False)

        self.content.show_all()

    def add_network(self, ssid, show=True):
        _ = self.lang.gettext

        netinfo = self._screen.wifi.get_network_info(ssid)
        if netinfo == None:
            logging.debug("Couldn't get netinfo for %s" % ssid)
            return
        logging.debug("Adding network %s" % ssid)

        configured_networks = self._screen.wifi.get_supplicant_networks()
        network_id = -1
        for net in list(configured_networks):
            if configured_networks[net]['ssid'] == ssid:
                network_id = net

        frame = Gtk.Frame()
        frame.set_property("shadow-type",Gtk.ShadowType.NONE)
        frame.get_style_context().add_class("frame-item")


        name = Gtk.Label()
        name.set_markup("<big><b>%s</b></big>" % (ssid))
        name.set_hexpand(True)
        name.set_halign(Gtk.Align.START)
        name.set_line_wrap(True)
        name.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)

        stream = os.popen('ip add show dev %s' % self.interface)
        content = stream.read()
        ipv4_re = re.compile(r'inet ([0-9\.]+)/[0-9]+', re.MULTILINE)
        ipv6_re = re.compile(r'inet6 ([a-fA-F0-9:\.]+)/[0-9+]', re.MULTILINE)
        match = ipv4_re.search(content)
        ipv4 = ""
        if match:
            ipv4 = "<b>%s:</b> %s " % (_("IPv4"), match.group(1))
        match = ipv6_re.search(content)
        ipv6 = ""
        if match:
            ipv6 = "<b>%s:</b> %s " % (_("IPv6"), match.group(1))


        stream = os.popen('hostname -f')
        hostname = stream.read().strip()

        logging.debug("netinfo: %s" % netinfo)
        connected = ""
        if netinfo['connected'] == True:
            connected = "<b>%s</b>\n<b>%s:</b> %s\n%s%s\n" % (_("Connected"),_("Hostname"),hostname, ipv4, ipv6)
        elif "psk" in netinfo:
            connected = "Password saved."
        freq = "2.4 GHz" if netinfo['frequency'][0:1] == "2" else "5 Ghz"
        info = Gtk.Label()
        info.set_markup("%s%s <small>%s %s %s  %s%s</small>" % ( connected,
            "" if netinfo['encryption'] == "off" else netinfo['encryption'].upper(),
            freq, _("Channel"), netinfo['channel'], netinfo['signal_level_dBm'], _("dBm")
            ))
        info.set_halign(Gtk.Align.START)
        #info.set_markup(self.get_file_info_str(ssid))
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        labels.add(name)
        labels.add(info)
        labels.set_vexpand(True)
        labels.set_valign(Gtk.Align.CENTER)
        labels.set_halign(Gtk.Align.START)

        connect = self._gtk.ButtonImage("open",None,"color3")
        connect.connect("clicked", self.connect_network, ssid)
        connect.set_hexpand(False)
        connect.set_halign(Gtk.Align.END)

        delete = self._gtk.ButtonImage("decrease",_("Delete"),"color3")
        delete.connect("clicked", self.remove_wifi_network, ssid)
        delete.set_size_request(60,0)
        delete.set_hexpand(False)
        delete.set_halign(Gtk.Align.END)

        network = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        network.set_hexpand(True)
        network.set_vexpand(False)

        network.add(labels)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        if network_id != -1:
            buttons.pack_end(delete, False, False, 0)
        if netinfo['connected'] == False:
            buttons.pack_end(connect, False, False, 0)

        network.add(buttons)

        self.networks[ssid] = frame
        frame.add(network)

        reverse = False

        pos = 0
        if netinfo['connected'] == True:
            logging.info("%s at pos 0" % ssid)
            pos = 0
        else:
            connected_ssid = self._screen.wifi.get_connected_ssid()
            logging.info("Connected ssid: %s" % connected_ssid)
            nets = list(self.networks)
            logging.info("Nets: %s" % nets)
            if connected_ssid != None:
                if connected_ssid in nets:
                    nets.remove(connected_ssid)
            nets = sorted(nets, reverse=reverse)
            logging.info("Nets: %s" % nets)
            pos = nets.index(ssid)
            if connected_ssid != None:
                pos += 1

        logging.info("Adding SSID %s at pos %s" % (ssid, pos))

        self.labels['networks'][ssid] = {
            "connect": connect,
            "delete": delete,
            "info": info,
            "name": name,
            "row": network
        }

        logging.info("Creating row")
        self.labels['networklist'].insert_row(pos)
        logging.info("Attaching row")
        self.labels['networklist'].attach(self.networks[ssid], 0, pos, 1, 1)
        if show == True:
            logging.info("Showing row")
            self.labels['networklist'].show()
        logging.info("Showing network info")

        i = 0
        while self.labels['networklist'].get_child_at(0, i) != None:
            logging.info("%s: %s" % (i, self.labels['networklist'].get_child_at(0, i)))
            i = i+1

    def remove_network_wid(self, widget, ssid):
        self.remove_network(ssid)

    def remove_network(self, ssid, show=True):
        if ssid not in self.networks:
            return

        i = 0
        while self.labels['networklist'].get_child_at(0, i) != None:
            logging.info("%s: %s %s" % (i, self.labels['networklist'].get_child_at(0, i), self.networks[ssid]))
            if self.networks[ssid] == self.labels['networklist'].get_child_at(0, i):
                self.labels['networklist'].remove_row(i)
                del self.networks[ssid]
                del self.labels['networks'][ssid]
                logging.info("Found, returning")
                return
            i = i+1
        return

    def add_new_network(self, widget, ssid, connect=False):
        networks = self._screen.wifi.get_networks()
        logging.debug("networks: %s" % networks)
        #if networks.
        psk = self.labels['network_psk'].get_text()
        result = self._screen.wifi.add_network(ssid, psk)

        self.close_add_network()

        if connect == True:
            if result == True:
                self.connect_network(widget, ssid, False)
            else:
                self._screen.show_popup_message("Error adding network %s" % ssid)


    def check_missing_networks(self):
        logging.info("Checking missing networks")
        networks = self._screen.wifi.get_networks()
        logging.info("Check missing networks (scan, displayed): %s %s" % (networks, list(self.networks)))
        for net in list(self.networks):
            if net in networks:
                networks.remove(net)
        logging.info("Check missing networks (scan, displayed): %s %s" % (networks, list(self.networks)))
        for net in networks:
            self.add_network(net)

    def connect_network(self, widget, ssid, showadd=True):
        _ = self.lang.gettext

        snets = self._screen.wifi.get_supplicant_networks()
        isdef = False
        for id, net in snets.items():
            if net['ssid'] == ssid:
                isdef = True
                break

        if isdef == False:
            if showadd == True:
                self.show_add_network(widget, ssid)
            return
        self.prev_network = self._screen.wifi.get_connected_ssid()

        buttons = [
            {"name": _("Close"), "response": Gtk.ResponseType.CANCEL}
        ]

        scroll = Gtk.ScrolledWindow()
        scroll.set_property("overlay-scrolling", False)
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.set_size_request(800,400)
        self.labels['connecting_info'] = Gtk.Label(_("Starting WiFi Re-association"))
        self.labels['connecting_info'].set_halign(Gtk.Align.START)
        self.labels['connecting_info'].set_valign(Gtk.Align.START)
        scroll.add(self.labels['connecting_info'])
        dialog = self._gtk.Dialog(self._screen, buttons, scroll, self.close_dialog)
        self._screen.show_all()

        if ssid in self.networks:
            self.remove_network(ssid)
        if self.prev_network in self.networks:
            self.remove_network(self.prev_network)
            #GLib.timeout_add(500, self.add_network, self.prev_network)

        self._screen.wifi.add_callback("connecting_status", self.connecting_status_callback)
        self._screen.wifi.connect(ssid)

    def connected_callback(self, ssid, prev_ssid):
        logging.info("Now connected to '%s' from '%s'" % (ssid, prev_ssid))
        if ssid != None:
            self.remove_network(ssid)
        if prev_ssid != None:
            self.remove_network(prev_ssid)
            
        self.check_missing_networks()

    def connecting_status_callback(self, msg):
        logging.info("Adding info: %s" % msg)
        self.labels['connecting_info'].set_text(self.labels['connecting_info'].get_text() + "\n" + msg)
        self.labels['connecting_info'].show_all()

    def close_dialog(self, widget, response_id):
        widget.destroy()

        #self.add_network(self.prev_network)
        #cur_ssid = self._screen.wifi.get_connected_ssid()
        #self.add_network()



    def scan_callback(self, new_networks, old_networks):
        for net in new_networks:
            self.add_network(net, False)
        for net in old_networks:
            self.remove_network(net, False)
        self.content.show_all()

    def close_add_network(self, widget, ssid):
        for child in self.content.get_children():
            self.content.remove(child)
        self.content.add(self.labels['main_box'])
        self.content.show()

    def remove_wifi_network(self, widget, ssid):
        self._screen.wifi.delete_network(ssid)
        self.remove_network(ssid)
        self.check_missing_networks()

    def show_add_network(self, widget, ssid):
        _ = self.lang.gettext
        logging.debug("Adding show network for %s" % ssid)
        for child in self.content.get_children():
            self.content.remove(child)

        if "add_network" in self.labels:
            del self.labels['add_network']

        self.labels['add_network'] = Gtk.VBox()
        self.labels['add_network'].set_valign(Gtk.Align.START)

        box = Gtk.Box(spacing=5)
        box.set_size_request(self._gtk.get_content_width(), self._gtk.get_content_height() -
                self._screen.keyboard_height - 20)
        box.set_hexpand(True)
        box.set_vexpand(False)
        self.labels['add_network'].add(box)

        l = self._gtk.Label("%s %s:" % (_("PSK for"), ssid))
        l.set_hexpand(False)
        entry = Gtk.Entry()
        entry.set_hexpand(True)

        save = self._gtk.ButtonImage("sd",_("Save"),"color3")
        save.set_hexpand(False)
        save.connect("clicked", self.add_new_network, ssid, True)


        self.labels['network_psk'] = entry
        box.pack_start(l, False, False, 5)
        box.pack_start(entry, True, True, 5)
        box.pack_start(save, False, False, 5)

        self.show_create = True
        self.labels['network_psk'].set_text('')
        self.content.add(self.labels['add_network'])
        self.content.show()
        logging.debug("Showing keyboard")
        self._screen.show_keyboard()
        self.labels['network_psk'].grab_focus_without_selecting()
