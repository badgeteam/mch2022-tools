#!/usr/bin/env python3
from webusb import *
import argparse
import sys
import time

def type_to_name(type_number):
    if type_number == 0x01:
        return "uint8"
    if type_number == 0x11:
        return "int8"
    if type_number == 0x02:
        return "uint16"
    if type_number == 0x12:
        return "int16"
    if type_number == 0x04:
        return "uint32"
    if type_number == 0x14:
        return "int32"
    if type_number == 0x08:
        return "uint64"
    if type_number == 0x18:
        return "int64"
    if type_number == 0x21:
        return "string"
    if type_number == 0x42:
        return "blob"
    return str(type_number)

def should_read(type_number):
    if type_number == 0x01:
        return True
    if type_number == 0x11:
        return True
    if type_number == 0x02:
        return True
    if type_number == 0x12:
        return True
    if type_number == 0x04:
        return True
    if type_number == 0x14:
        return True
    if type_number == 0x08:
        return True
    if type_number == 0x18:
        return True
    if type_number == 0x21:
        return True
    return False

parser = argparse.ArgumentParser(description='MCH2022 badge NVS list tool')
parser.add_argument("namespace", help="Namespace", nargs='?', default=None)
args = parser.parse_args()

badge = Badge()

if not badge.begin():
    print("Failed to connect")
    sys.exit(1)

print("\x1b[4m{: <32}\x1b[0m \x1b[4m{: <32}\x1b[0m \x1b[4m{: <8}\x1b[0m \x1b[4m{: <10}\x1b[0m \x1b[4m{: <32}\x1b[0m".format("Namespace", "Key", "Type", "Size", "Value"))
badge.printGarbage = True
if args.namespace:
    entries = badge.nvs_list(args.namespace)
else:
    entries = badge.nvs_list()
for namespace in entries:
    for entry in entries[namespace]:
        value = "..."
        if entry["size"] < 64 and should_read(entry["type"]):
            value = str(badge.nvs_read(namespace, entry["key"], entry["type"]))
        print("{: <32} {: <32} {: <8} {:10d} {}".format(namespace, entry["key"], type_to_name(entry["type"]), entry["size"], value))
