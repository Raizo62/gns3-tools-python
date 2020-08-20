#!/usr/local/bin/python3
"""
export_template.py - Export Template as an Appliance
"""

import os
import sys
import json
import re
from collections import OrderedDict
import gns3api
from qt_widgets import SimpleWidgets

widget = SimpleWidgets()

def die(text):
    """ terminate program with error message """
    widget.alert(None, text)
    sys.exit(text)


# get command line parameter
if len(sys.argv) < 3:
    die("usage: export_template version parameter-file [project-id [sel-item ...]]")
try:
    with open(sys.argv[2], "r") as file:
        cntl_url, cntl_user, cntl_passwd, *_ = file.read(512).splitlines()
    if sys.argv[2].endswith(".tmp"):
        os.remove(sys.argv[2])
except (OSError, ValueError) as err:
    die("Can't get controller connection params: {}".format(err))
version = sys.argv[1]

# check version
ver_match = re.match(r'[vV]?(\d+)\.(\d+)', version)
if ver_match:
    ver_tuple = tuple(map(int, ver_match.groups()))
if not ver_match or ver_tuple < (2, 2):
    die("Unsupported version {}, need at least 2.2".format(version))

# connect to GNS3 controller
try:
    api = gns3api.GNS3Api(cntl_url, cntl_user, cntl_passwd)
except gns3api.GNS3ApiException as err:
    die("Can't connect to GNS3 controller: {}".format(err))

template_name = widget.get_text(None, "Template name:")
if not template_name:
    sys.exit(0)

template = None
try:
    for template in api.request("GET", "/v2/templates"):
        if template["name"] == template_name:
            break
    else:
        die("Template '{}' not found".format(template_name))
except gns3api.GNS3ApiException as err:
    die("Can't get templates: {}".format(err))

if template["template_type"] not in ("docker", "dynamips", "iou", "qemu"):
    die("Unsupported VM type '{}', must be docker, dynamips, iou or qemu."
        .format(template["template_type"]))

# basic information
gns3a = OrderedDict()
gns3a["name"]             = template["name"]
if template["category"] == "switch":
    gns3a["category"]     = "multilayer_switch"
else:
    gns3a["category"]     = template["category"]
gns3a["description"]      = "Export of template '{}'".format(template["name"])
gns3a["vendor_name"]      = "unknown"
gns3a["vendor_url"]       = "http://www.example.com"
gns3a["product_name"]     = template["name"]
gns3a["registry_version"] = 3
gns3a["status"]           = "experimental"
gns3a["maintainer"]       = "Unknown"
gns3a["maintainer_email"] = "unknown@example.org"
for key in ("usage", "symbol", "first_port_name", "port_name_format"):
    if template.get(key):
        gns3a[key] = template[key]
if not template.get("linked_clone", True):
    gns3a["linked_clone"] = False
    gns3a["registry_version"] = 4

vm_images = OrderedDict()

# Docker
if template["template_type"] == "docker":
    docker = OrderedDict()
    gns3a["docker"] = docker
    docker["adapters"] = template.get("adapters", 1)
    for key in ("image", "start_command", "environment",
                "console_type", "console_http_port", "console_http_path"):
        if template.get(key):
            docker[key] = template[key]
    if docker["image"].endswith(":latest"):
        docker["image"] = docker["image"][:-7]
    if docker.get("console_type") not in ("http", "https"):
        docker.pop("console_http_port", None)
        docker.pop("console_http_path", None)

# Dynamips
elif template["template_type"] == "dynamips":
    dynamips = OrderedDict()
    gns3a["dynamips"] = dynamips
    for key in ("chassis", "platform", "ram", "nvram", "startup_config",
                "wic0", "wic1", "wic2", "slot0", "slot1", "slot2", "slot3",
                "slot4", "slot5", "slot6", "midplane", "npe"):
        if template.get(key):
            dynamips[key] = template[key]
    vm_images["image"] = template["image"]

# IOU VM
elif template["template_type"] == "iou":
    iou = OrderedDict()
    gns3a["iou"] = iou
    for key in ("ethernet_adapters", "serial_adapters",
                "nvram", "ram", "startup_config"):
        iou[key] = template[key]
    vm_images["image"] = template["path"]

# QEMU
elif template["template_type"] == "qemu":
    qemu = OrderedDict()
    gns3a["qemu"] = qemu
    qemu["adapter_type"] = template.get("adapter_type", "e1000")
    qemu["adapters"] = template.get("adapters", 1)
    if template.get("custom_adapters"):
        qemu["custom_adapters"] = template["custom_adapters"]
        gns3a["registry_version"] = max(gns3a["registry_version"], 6)
    qemu["ram"] = template.get("ram", 256)
    if template.get("cpus", 1) >= 2:
        qemu["cpus"] = template["cpus"]
        gns3a["registry_version"] = max(gns3a["registry_version"], 4)
    for key in ("kernel_image", "initrd", "bios_image"):
        if template.get(key):
            vm_images[key] = template[key]
    if "bios_image" in vm_images:
        gns3a["registry_version"] = max(gns3a["registry_version"], 4)
    for key in ("hda", "hdb", "hdc", "hdd"):
        hd_image = key + "_disk_image"
        hd_intf = key + "_disk_interface"
        if template.get(hd_image):
            vm_images[hd_image] = template[hd_image]
            qemu[hd_intf] = template.get(hd_intf, "ide")
            if qemu[hd_intf] == "sata":
                gns3a["registry_version"] = max(gns3a["registry_version"], 4)
    if template.get("cdrom_image"):
        vm_images["cdrom_image"] = template["cdrom_image"]
    match = re.search(r'qemu-system-([^/\\]*)$', template["qemu_path"])
    if match:
        qemu["arch"] = match.group(1)
    else:
        qemu["arch"] = "i386"
    qemu["console_type"] = template.get("console_type", "telnet")
    if qemu["console_type"] == "spice":
        gns3a["registry_version"] = max(gns3a["registry_version"], 5)
    if template.get("boot_priority") and template["boot_priority"] != "c":
        qemu["boot_priority"] = template["boot_priority"]
    if template.get("kernel_command_line"):
        qemu["kernel_command_line"] = template["kernel_command_line"]
    qemu["kvm"] = "allow"
    options = template.get("options")
    if options:
        options, changes = re.subn(r'\s*-no-kvm\b', "", options)
        if changes:
            qemu["kvm"] = "disable"
        options = re.sub(r'\s*-nographic\b', "", options)
        options = options.strip()
    if options:
        qemu["options"] = options
    if template.get("cpu_throttling"):
        qemu["cpu_throttling"] = template["cpu_throttling"]
    if template.get("process_priority") and \
       template["process_priority"] != "normal":
        qemu["process_priority"] = template["process_priority"]

# Images
image_version = "0.0"
if vm_images:
    try:
        image_list = api.request("GET", ("/v2/computes",
                                         template["compute_id"],
                                         template["template_type"],
                                         "images"))
    except gns3api.GNS3ApiException as err:
        die("Can't get image list: {}".format(err))

    images = []
    version_images = OrderedDict()
    for image_type, path in vm_images.items():
        filename = re.split(r'[/\\]', path)[-1]
        filesize = 0
        md5sum = "00000000000000000000000000000000"
        for image_info in image_list:
            if image_info["filename"] == filename:
                filesize = image_info["filesize"]
                md5sum = image_info["md5sum"]
                break
        image = OrderedDict()
        image["filename"] = filename
        image["version"] = image_version
        image["md5sum"] = md5sum
        image["filesize"] = filesize
        images.append(image)
        version_images[image_type] = filename
    gns3a["images"] = images
    version_ver = OrderedDict()
    version_ver["name"] = image_version
    if template.get("idlepc"):
        version_ver["idlepc"] = template["idlepc"]
    version_ver["images"] = version_images
    gns3a["versions"] = [version_ver]

# save appliance
ofile = widget.get_save_filename("Save appliance", "~",
                                 (("GNS3 Appliance", "*.gns3a *.gns3appliance"),
                                  ("all files", "*")))
if not ofile:
    sys.exit(0)
try:
    with open(ofile, "w") as f_out:
        json.dump(gns3a, f_out, indent=4, separators=(",", ": "))
        f_out.write("\n")
except OSError as err:
    die("Can't save appliance: {}".format(err))
