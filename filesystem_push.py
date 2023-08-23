#!/usr/bin/env python3

from webusb import *
import argparse
import sys
import time

parser = argparse.ArgumentParser(description='MCH2022 badge FAT filesystem file upload tool')
parser.add_argument("name", help="Local file")
parser.add_argument("target", help="Remote file")
args = parser.parse_args()

name = args.name
target = args.target

if not (target.startswith("/internal") or target.startswith("/sd")):
    print("Path should always start with /internal or /sd")
    sys.exit(1)


if target.endswith("/"):
    target = target[:-1]

badge = Badge()

if not badge.begin():
    print("Failed to connect")
    sys.exit(1)

def upload_file(name, target):
    with open(name, "rb") as f:
        data = f.read()

    result = badge.fs_write_file(target.encode("ascii", "ignore"), data)
    if result:
        print(f"File {name} pushed succesfully to {target}")
    else:
        print(f"Failed to push file {name} to {target}")
        sys.exit(1)

if os.path.isdir(name):
    for root, dirs, files in os.walk(name, topdown=True):
        for filename in files:
            upload_file(
                os.path.join(root, filename),
                os.path.join(target + root[len(name) :], filename),
            )
        for dirname in dirs:
            badge.fs_create_directory(
                os.path.join(target + root[len(name) :], dirname).encode(
                    "ascii", "ignore"
                )
            )
else:
    upload_file(name, target)
