#!/usr/bin/env python3
from webusb import *
import argparse

parser = argparse.ArgumentParser(description='MCH2022 file listing tool')
parser.add_argument("--address", help="USB device address", default=None)
args = parser.parse_args()

dev = WebUSB(address=args.address)
apps = dev.appfsList()

print("Number of apps:", len(apps))

print("{0: <5}  {1:}".format("size", "name"))
print("==============================")
for app in apps:
    appsize = app["size"]
    appname = app["name"]
    print("{0: <5}  \"{1:}\"".format(appsize, appname))
