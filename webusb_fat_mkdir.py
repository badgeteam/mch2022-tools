#!/usr/bin/env python3
from webusb import *
import argparse

parser = argparse.ArgumentParser(description='MCH2022 badge FAT FS mkdir tool')
parser.add_argument("name", help="directory name")
args = parser.parse_args()

name = args.name
dev = WebUSB()
res = dev.makeFSDir(name)
if res:
    print("Directory created")
else:
    print("Directory creation failed")
