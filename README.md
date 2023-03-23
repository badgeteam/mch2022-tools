## Using WebUSB tools
This directory contains command line tools for use with your badge.

To use them, you will need to `pip install pyusb`.

### Application management
The AppFS contains binary ESP32 apps - standalone firmwares that can be booted and used as apps.

`app_list.py`
Lists all apps on the AppFS.

`app_push.py {file} {name} {title} {version} [--run]`
Installs an ESP32 app to the AppFS.
The `--run` flag will also immediately start the app after installing.

`app_pull.py {name} {target}`
Downloads the ESP32 app binary to your computer, the file will be saved at the location provided as target.

`app_run.py {name}`
Boots an ESP32 app with the specified name.

`webusb_remove.py {app_name}`
Removes an ESP32 app from the AppFS.

### FAT filesystem
`filesystem_list.py [path] [--recursive]`
Returns a directory listing for the specified path.

`filesystem_push.py {filename} {target_location}`
Uploads a file to the FAT filesystem.
`target_location` should always start with `/internal` or `/sd` and include the target filename.

...

### Configuration management

...

### FPGA
`webusb_fpga.py {filename} [bindings]`
Loads a bit stream from a file into the FPGA.

### Other
`exit.py`
Reboots the badge, exiting webusb mode.
