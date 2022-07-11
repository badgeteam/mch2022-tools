#!/usr/bin/env python3
import os
import usb
import argparse

parser = argparse.ArgumentParser(description='MCH2022 badge listing tool')
parser.add_argument("--flat", help="Report only the addresses of each badge, or 'none' if none ar found.", action="store_true")
args = parser.parse_args()

iter=[]
if os.name == 'nt':
    from usb.backend import libusb1
    lube = libusb1.get_backend(find_library=lambda x: os.path.dirname(__file__) + "\\libusb-1.0.dll")
    iter = usb.core.find(idVendor=0x16d0, idProduct=0x0f9a, find_all=True, backend=lube)
else:
    iter = usb.core.find(idVendor=0x16d0, idProduct=0x0f9a, find_all=True)

list=[]
for dev in iter:
    if args.flat:
        list.append(f'{dev.address}')
    else:
        list.append(f'   badge {dev.address} (use --address={dev.address})')

if args.flat:
    if len(list) == 0:
        print("none")
else:
    if len(list) == 0:
        print("No MCH2022 badges found.")
    elif len(list) == 1:
        print("1 MCH2022 badge found:")
    else:
        print(f"{len(list)} MCH2022 badges found:")

for dev in list:
    print(dev)
