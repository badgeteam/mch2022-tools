#!/usr/bin/env python3
from webusb import *
import argparse

parser = argparse.ArgumentParser(description='MCH2022 badge AppFS reset tool')
parser.add_argument("--address", help="USB device address", default=None)
args = parser.parse_args()

dev = WebUSB(False, address=args.address)
dev.reset()
