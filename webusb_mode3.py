#!/usr/bin/env python3

import os
import usb.core
import usb.util
import binascii
import time
import sys
import struct
from datetime import datetime

class Badge:
    # Defined in webusb_task.c of the RP2040 firmware
    REQUEST_STATE          = 0x22
    REQUEST_RESET          = 0x23
    REQUEST_BAUDRATE       = 0x24
    REQUEST_MODE           = 0x25
    REQUEST_MODE_GET       = 0x26
    REQUEST_FW_VERSION_GET = 0x27

    # Defined in main.c of the ESP32 firmware
    BOOT_MODE_NORMAL        = 0x00
    BOOT_MODE_WEBUSB_LEGACY = 0x01
    BOOT_MODE_FPGA_DOWNLOAD = 0x02
    BOOT_MODE_WEBUSB        = 0x03
    
    MAGIC = 0xFEEDF00D

    def __init__(self):
        if os.name == 'nt':
            from usb.backend import libusb1
            be = libusb1.get_backend(find_library=lambda x: os.path.dirname(__file__) + "\\libusb-1.0.dll")
            self.device = usb.core.find(idVendor=0x16d0, idProduct=0x0f9a, backend=be)
        else:
            self.device = usb.core.find(idVendor=0x16d0, idProduct=0x0f9a)

        if self.device is None:
            raise ValueError("Badge not found")

        configuration = self.device.get_active_configuration()

        self.webusb_esp32 = configuration[(4,0)]

        self.esp32_ep_out = usb.util.find_descriptor(self.webusb_esp32, custom_match = lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
        self.esp32_ep_in  = usb.util.find_descriptor(self.webusb_esp32, custom_match = lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)

        self.request_type_in = usb.util.build_request_type(usb.util.CTRL_IN, usb.util.CTRL_TYPE_CLASS, usb.util.CTRL_RECIPIENT_INTERFACE)
        self.request_type_out = usb.util.build_request_type(usb.util.CTRL_OUT, usb.util.CTRL_TYPE_CLASS, usb.util.CTRL_RECIPIENT_INTERFACE)
        
        self.rx_data = bytes([])
        self.packets = []

    def send_packet(self, command = b"XXXX", payload = bytes([])):
        self.esp32_ep_out.write(struct.pack("<IIIII", self.MAGIC, 0x00000000, int.from_bytes(command, "little"), len(payload), binascii.crc32(payload)))
        if len(payload) > 0:
            self.esp32_ep_out.write(payload)

    def receive_data(self):
        t = 200
        while t > 0:
            try:
                new_data = bytes(self.esp32_ep_in.read(self.esp32_ep_in.wMaxPacketSize, 5))
                self.rx_data += new_data
                if len(new_data) > 0:
                    t = 200
            except Exception as e:
                t-=1

    def receive_packets(self):
        garbage = bytearray()
        self.receive_data()
        if len(self.rx_data) < 20: # length of header
            return False
        while len(self.rx_data) >= 20:
            header = struct.unpack("<IIIII", self.rx_data[:20])
            if header[0] != self.MAGIC:
                garbage.append(self.rx_data[0])
                self.rx_data = self.rx_data[1:]
                continue
            identifier = header[1]
            command = header[2]
            command_ascii = struct.pack("<I", command)
            payload_length = header[3]
            payload_crc = header[4]
            if (len(self.rx_data) - 20) < payload_length:
                print("Got header, not enough data")
                break
            #print("Receive payload length", command_ascii, payload_length)
            self.rx_data = self.rx_data[20:]
            payload = self.rx_data[:payload_length]
            self.rx_data = self.rx_data[payload_length:]
            payload_crc_check = binascii.crc32(payload)
            if payload_crc != payload_crc_check:
                #print("payload", payload)
                print("Payload CRC doesn't match {:08X} {:08X}".format(payload_crc, payload_crc_check))
                #continue
            self.packets.append({
                "identifier": identifier,
                "command": command_ascii,
                "payload": payload
            })
        if len(garbage) > 0:
            print("Garbage:", garbage)
        return True
    
    def receive_packet(self):
        self.receive_packets()
        #print(self.packets)
        packet = None
        if len(self.packets) > 0:
            packet = self.packets[0]
            self.packets = self.packets[1:]
        return packet
    
    def peek_packet(self):
        self.receive_packets()
        packet = None
        if len(self.packets) > 0:
            packet = self.packets[0]
        return packet
    
    def sync(self):
        self.receive_packets()
        self.packets = []
        self.send_packet(b"SYNC")
        response = self.receive_packet()
        if not response:
            print("No response")
            return False
        if not response["command"] == b"SYNC":
            return False
        return True

    def ping(self, payload):
        self.send_packet(b"PING", payload)
        response = self.receive_packet()
        if not response:
            print("No response")
            return False
        if not response["command"] == b"PING":
            print("No PING", response["command"])
            return False
        if not response["payload"] == payload:
            print("Payload mismatch", payload, response["payload"])
            for i in range(len(payload)):
                print(i, int(payload[i]), int(response["payload"][i]))
            return False
        return True
    
    def fs_list(self, payload):
        self.send_packet(b"FSLS", payload + b"\0")
        response = self.receive_packet()
        if not response:
            print("No response")
            return None
        if not response["command"] == b"FSLS":
            if not response["command"] == b"ERR5": # Failed to open directory
                print("No FSLS", response["command"])
            return None
        payload = response["payload"]

        output = []
        
        while len(payload) > 0:
            data = payload[:1 + 4]
            payload = payload[1 + 4:]
            (item_type, item_name_length) = struct.unpack("<BI", data)
            name = payload[:item_name_length]
            payload = payload[item_name_length:]
            data = payload[:4 + 4 + 8]
            payload = payload[4 + 4 + 8:]
            (stat_res, item_size, item_modified) = struct.unpack("<IIQ", data)
            stat = None
            if stat_res == 0:
                stat = {
                    "size": item_size,
                    "modified": item_modified
                }
            item = {
                "type": item_type,
                "name": name,
                "stat": stat
            }
            output.append(item)
        return output

    def fs_file_exists(self, name):
        self.send_packet(b"FSEX", name)
        response = self.receive_packet()
        if not response:
            print("No response to FSEX")
            return False
        if not response["command"] == b"FSEX":
            print("No FSEX", response["command"])
            return False
        payload = response["payload"]
        if not len(payload) == 1:
            print("Wrong payload length")
            return False
        return True if payload[0] else False

    def fs_create_directory(self, name):
        self.send_packet(b"FSMD", name)
        response = self.receive_packet()
        if not response:
            print("No response to FSMD")
            return False
        if not response["command"] == b"FSMD":
            print("No FSMD", response["command"])
            return False
        payload = response["payload"]
        if not len(payload) == 1:
            print("Wrong payload length")
            return False
        return True if payload[0] else False

    def fs_remove(self, name):
        self.send_packet(b"FSRM", name)
        response = self.receive_packet()
        if not response:
            print("No response to FSRM")
            return False
        if not response["command"] == b"FSRM":
            print("No FSRM", response["command"])
            return False
        payload = response["payload"]
        if not len(payload) == 1:
            print("Wrong payload length")
            return False
        return True if payload[0] else False

    def fs_state(self, name):
        raise Exception("Not implemented")

    def fs_write_file(self, name, data):
        self.send_packet(b"FSFW", name)
        response = self.receive_packet()
        if not response:
            print("No response FSFW")
            return False
        if not response["command"] == b"FSFW":
            print("No FSFW", response["command"])
            return False
        payload = response["payload"]
        if not payload[0]:
            print("Failed to open file")
            return False
        position = 0

        while True:
            print("Position", position)
            chunk = data[position:position+8192]
            position += 8192
            if len(chunk) < 1:
                break
            print("Sending", position, len(chunk))
            sent = self.fs_write_chunk(chunk)
            if sent != len(chunk):
                print("Failed to send data", sent, len(chunk))
                self.fs_close_file()
                return False
        self.fs_close_file()
        return True

    def fs_write_chunk(self, data):
        self.send_packet(b"CHNK", data)
        response = self.receive_packet()
        if not response:
            print("No response CHNK write")
            return False
        if not response["command"] == b"CHNK":
            print("No CHNK", response["command"])
            return False
        return struct.unpack("<I", response["payload"])[0]

    def fs_read_file(self, name):
        self.send_packet(b"FSFR", name)
        response = self.receive_packet()
        if not response:
            print("No response FSFR")
            return False
        if not response["command"] == b"FSFR":
            print("No FSFR", response["command"])
            return False
        payload = response["payload"]
        print("payload", payload)

        if not payload[0]:
            print("Failed to open file")
            return False
        
        data = bytearray()

        while True:
            datanew = self.read_chunk()
            if datanew == None:
                print("Read error!")
                return False
            data += datanew
            print("RX", len(datanew), len(data))
            if len(datanew) < 1:
                break
        self.fs_close_file()
        return data

    def fs_close_file(self):
        self.send_packet(b"FSFC")
        response = self.receive_packet()
        if not response:
            print("No response to FSFC")
            return False
        if not response["command"] == b"FSFC":
            print("No FSFC", response["command"])
            return False
        payload = response["payload"]
        if not len(payload) == 1:
            print("Wrong payload length")
            return False
        return True if payload[0] else False
    
    def read_chunk(self):
        self.send_packet(b"CHNK")
        response = self.receive_packet()
        if not response:
            print("No response CHNK read")
            return False
        if not response["command"] == b"CHNK":
            print("No CHNK", response["command"])
            return False
        payload = response["payload"]
        return payload

    def app_list(self):
        self.send_packet(b"APPL")
        response = self.receive_packet()
        if not response:
            print("No response")
            return None
        if not response["command"] == b"APPL":
            print("No APPL", response["command"])
            return None
        payload = response["payload"]

        output = []

        while len(payload) > 0:
            name_length = header = struct.unpack("<H", payload[:2])[0]
            payload = payload[2:]
            name = payload[:name_length]
            payload = payload[name_length:]
            title_length = header = struct.unpack("<H", payload[:2])[0]
            payload = payload[2:]
            title = payload[:title_length]
            payload = payload[title_length:]
            (version, size) = struct.unpack("<HI", payload[:6])
            payload = payload[6:]

            output.append({
                "name": name,
                "title": title,
                "version": version,
                "size": size
            })
        return output

    def app_read(self, name):
        raise Exception("Not implemented")

    def app_write(self, name):
        raise Exception("Not implemented")

    def nvs_list(self, namespace):
        raise Exception("Work in progress")
        self.send_packet(b"NVSL", namespace + b"\0")
        response = self.receive_packet()
        if not response:
            print("No response")
            return None
        if not response["command"] == b"NVSL":
            print("No NVSL", response["command"])
            return None
        payload = response["payload"]

        print(payload)

        output = []

        return output

    def reset(self):
        self.device.ctrl_transfer(self.request_type_out, self.REQUEST_STATE, 0x0000, self.webusb_esp32.bInterfaceNumber) # Connect
        self.device.ctrl_transfer(self.request_type_out, self.REQUEST_MODE, self.BOOT_MODE_NORMAL, self.webusb_esp32.bInterfaceNumber)
        self.device.ctrl_transfer(self.request_type_out, self.REQUEST_RESET, 0x0000, self.webusb_esp32.bInterfaceNumber)
        self.device.ctrl_transfer(self.request_type_out, self.REQUEST_BAUDRATE, 1152, self.webusb_esp32.bInterfaceNumber)
    
    def start_webusb(self):
        self.device.ctrl_transfer(self.request_type_out, self.REQUEST_STATE, 0x0001, self.webusb_esp32.bInterfaceNumber) # Connect
        current_mode = int(self.device.ctrl_transfer(self.request_type_in, self.REQUEST_MODE_GET, 0, self.webusb_esp32.bInterfaceNumber, 1)[0]) # Read WebUSB mode

        if current_mode != self.BOOT_MODE_WEBUSB:
            print("Starting new webusb mode...")
            self.device.ctrl_transfer(self.request_type_out, self.REQUEST_MODE, self.BOOT_MODE_WEBUSB, self.webusb_esp32.bInterfaceNumber)
            self.device.ctrl_transfer(self.request_type_out, self.REQUEST_RESET, 0x0000, self.webusb_esp32.bInterfaceNumber)
            self.device.ctrl_transfer(self.request_type_out, self.REQUEST_BAUDRATE, 9216, self.webusb_esp32.bInterfaceNumber)
            #self.device.ctrl_transfer(self.request_type_out, self.REQUEST_BAUDRATE, 1152, self.webusb_esp32.bInterfaceNumber)

badge = Badge()

if not badge.sync():
    print("Connecting...")
    badge.start_webusb()
    time.sleep(1)
    if not badge.sync():
        print("Reset...")
        badge.reset()
        badge.start_webusb()
        time.sleep(1)
        if not badge.sync():
            print("Failed to connect to the badge")
            sys.exit(1)

print("Connected")

bigdata8 = bytearray([0] * 1024 * 8)
for i in range(1024 * 8):
    bigdata8[i] = i % 256
bigdata4 = bytearray([0] * 1024 * 4)
for i in range(1024 * 4):
    bigdata4[i] = i % 256
bigdata2 = bytearray([0] * 1024 * 2)
for i in range(1024 * 2):
    bigdata2[i] = i % 256

#print("ping 8KB", badge.ping(bigdata8))
#print("ping 4KB", badge.ping(bigdata4))
#print("ping 2KB", badge.ping(bigdata2))
#print("ping", badge.ping(b"Hello world"))

def listall(location):
    filelist = badge.fs_list(location)
    if not filelist == None:
        for f in filelist:
            if f["type"] == 2:
                print("[DIR] ", end="")
            else:
                print("      ", end="")
            newlocation = location + b"/" + f["name"]
            locationstring = newlocation.decode("ascii")
            locatinstringpadding = " " * (64 - len(locationstring)) if len(locationstring) < 64 else ""
            print(locationstring + locatinstringpadding, end="")
            sizestring = ""
            modifiedstring = ""
            if f["stat"]:
                if f["type"] != 2:
                    s = f["stat"]["size"]
                    if s >= 1024:
                        sizestring = str(round(s / 1024, 2)) + " KB"
                    else:
                        sizestring = str(s) + " B"
                modifiedstring = datetime.utcfromtimestamp(f["stat"]["modified"]).strftime('%Y-%m-%d %H:%M:%S')
            sizestringpadding = " " * (16 - len(sizestring)) if len(sizestring) < 16 else ""
            print(sizestring + sizestringpadding, end="")
            print(modifiedstring, end="")
            print()
            if f["type"] == 2:
                listall(newlocation)
    else:
        print(location.decode("ascii") + " ** Failed to open directory **")

#listall(b"/internal")

#print("List not existing")
#listall(b"/internal/bullshit")
#print("Create", badge.fs_create_directory(b"/internal/bullshit"))
#print("List existing")
#listall(b"/internal/bullshit")
#print("Remove", badge.fs_remove(b"/internal/bullshit"))
#print("List not existing")
#listall(b"/internal/bullshit")
"""
readres = badge.fs_read_file(b"/internal/apps/ice40/ice40_doom/icon.png\0")

with open("blah", "bw") as f:
    f.write(readres)

print("READ", readres)
"""
"""
with open("input", "rb") as f:
    data = f.read()

writeres = badge.fs_write_file(b"/internal/test.png\0", data)

print("WRITE", writeres)

readres = badge.fs_read_file(b"/internal/test.png\0")

with open("output", "bw") as f:
    f.write(readres)

print("READ", readres)

#{'type': 2, 'name': b'apps', 'stat': None}

#print("fsfr", badge.fs_read_file(b"/internal/apps/esp32/gnuboy/README.md"))
"""
"""
payload = b"/internal"
esp32_ep_out.write(struct.pack("<IIIII", 0xFEEDF00D, 0x00000000, int.from_bytes(b"FSLS", "little"), len(payload), binascii.crc32(payload)))
esp32_ep_out.write(payload)

data = bytes([])
t = 2000
while t > 0:
    try:
        new_data = bytes(esp32_ep_in.read(esp32_ep_in.wMaxPacketSize, 20))
        data += new_data
        if len(new_data) > 0:
            t = 20
    except Exception as e:
        t-=1

print(binascii.hexlify(data))
"""

#print("Apps", badge.app_list())

print("NVS", badge.nvs_list(b"system"))
