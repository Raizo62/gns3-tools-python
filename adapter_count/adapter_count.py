#!/usr/local/bin/python3

"""
adapter_count.py - change the number of adapters
"""

import os
import sys
import gns3api
from qt_widgets import SimpleWidgets

def die(text):
    """ terminate program with error message """
    SimpleWidgets().alert(None, text)
    sys.exit(text)


# get command line parameter
if len(sys.argv) < 4:
    die("usage:\ncadapter_count version parameter-file project-id [sel-item ...]")
try:
    with open(sys.argv[2], "r") as file:
        cntl_url, cntl_user, cntl_passwd, *_ = file.read(512).splitlines()
    if sys.argv[2].endswith(".tmp"):
        os.remove(sys.argv[2])
except (OSError, ValueError) as err:
    sys.exit("Can't get controller connection params: {}".format(err))
project_id = sys.argv[3]
sel_items = sys.argv[4:]

# get node id from command line
sel_nodes = [item[6:] for item in sel_items
             if item.startswith("nodes/")]
if len(sel_nodes) != 1:
    die("Exactly one node must be selected")
node_id = sel_nodes[0]

# connect to GNS3 controller
try:
    api = gns3api.GNS3Api(cntl_url, cntl_user, cntl_passwd)
except gns3api.GNS3ApiException as err:
    die("Can't connect to GNS3 controller: {}".format(err))

# get node information
try:
    node = api.request('GET', ('/v2/projects', project_id, 'nodes', node_id))
except gns3api.GNS3ApiException as err:
    die("Can't get node information: {}".format(err))

if node['node_type'] not in ("docker", "iou", "qemu"):
    die("Only the node types Docker, IOU and QEMU are supported")

if node['status'] != "stopped":
    die("Node must be stopped")

# New number of adapters
adapter_property = 'adapters'
if node['node_type'] == "iou":
    adapter_property = 'ethernet_adapters'
cur_adapters = node['properties'][adapter_property]
adapters = SimpleWidgets().get_int(None, "Adapters", cur_adapters, 1)
if adapters is None or adapters == cur_adapters:
    sys.exit(0)			# Nothing to do

# Get links of the node
try:
    links = api.request('GET', ('/v2/projects', project_id, 'nodes', node_id, 'links'))
except gns3api.GNS3ApiException as err:
    die("Can't get link information: {}".format(err))

# delete links of the node
try:
    for link in links:
        api.request('DELETE', ('/v2/projects', project_id, 'links', link['link_id']))
except gns3api.GNS3ApiException as err:
    die("Can't delete link: {}".format(err))

# update adapter count
update_err = None
try:
    api.request('PUT', ('/v2/projects', project_id, 'nodes', node_id),
                {'properties': {adapter_property: adapters}})
except gns3api.GNS3ApiException as err:
    update_err = "Can't update adapter count: {}".format(err)

# restore the links
for link in links:
    del link['link_id']
    try:
        api.request('POST', ('/v2/projects', project_id, 'links'), link)
    except gns3api.GNS3ApiException as err:
        if not isinstance(err, gns3api.HTTPError) or err.args[0] != 404:
            die("Can't restore link: {}".format(err))

if update_err:
    die(update_err)
