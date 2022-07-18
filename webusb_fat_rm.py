#!/usr/bin/env python3
from webusb import *
import argparse

parser = argparse.ArgumentParser(description='MCH2022 badge FAT FS remove tool')
parser.add_argument("name", help="filename")
args = parser.parse_args()

name = args.name
dev = WebUSB()
res = dev.removeFSFile(name)
if res:
    print("File removed")
else:
    print("File removal failed")
