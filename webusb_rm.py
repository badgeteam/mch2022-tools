#!/usr/bin/env python3
from webusb import *
import argparse

parser = argparse.ArgumentParser(description='MCH2022 badge AppFS remove tool')
parser.add_argument("name", help="AppFS filename")
parser.add_argument("--address", help="USB device address", default=None)
args = parser.parse_args()

dev = WebUSB(address=args.address)
res = dev.appfsRemove(args.name)

if res:
    print("App removed")
else:
    print("App removal failed")
