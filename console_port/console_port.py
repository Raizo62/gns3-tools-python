#!/usr/local/bin/python3

"""
console_port.py - change console port of one or more nodes
"""

import os
import sys
import gns3api
from qt_widgets import SimpleWidgets

widget = SimpleWidgets()

def die(text):
    """ terminate program with error message """
    widget.alert(None, text)
    sys.exit(text)

def set_console(argv):
    """ parse command line, retrieve nodes and set console port """

    # get arguments
    if len(argv) < 4:
        die("usage:\nconsole_port version parameter-file project-id [sel-item ...]")
    try:
        with open(argv[2], "r") as file:
            cntl_url, cntl_user, cntl_passwd, *_ = file.read(512).splitlines()
        if argv[2].endswith(".tmp"):
            os.remove(argv[2])
    except (OSError, ValueError) as err:
        sys.exit("Can't get controller connection params: {}".format(err))
    project_id = argv[3]
    sel_items = argv[4:]

    # connect to GNS3 controller
    try:
        api = gns3api.GNS3Api(cntl_url, cntl_user, cntl_passwd)
    except gns3api.GNS3ApiException as err:
        die("Can't connect to GNS3 controller: {}".format(err))

    # get node information
    nodes = {}
    try:
        for node in api.request('GET', ('/v2/projects', project_id, 'nodes')):
            nodes[node['node_id']] = node
    except gns3api.GNS3ApiException as err:
        die("Can't get node information: {}".format(err))
    if not nodes:
        die("No node in project")

    # get selected nodes
    if not sel_items:
        msg_type = "in project"
        sel_nodes = list(nodes.keys())
    else:
        msg_type = "selected"
        sel_nodes = [item[6:] for item in sel_items
                     if item.startswith("nodes/")]
        if not sel_nodes:
            die("No node selected")

    sel_nodes = [node_id for node_id in sel_nodes
                 if nodes[node_id]['console']]
    if not sel_nodes:
        die("No node with console port " + msg_type)
    sel_nodes.sort(key=lambda k: nodes[k]['name'].lower())

    # New console port
    min_port = 5000
    max_port = 10000
    console_port = widget.get_int(None, "Console port", min_port,
                                  min_port, max_port)
    if console_port is None:
        return

    # update console port of selected nodes
    for node_id in sel_nodes:
        if nodes[node_id]['node_type'] == 'ethernet_switch':
            continue
        try:
            node = api.request('PUT',
                               ('/v2/projects', project_id, "nodes", node_id),
                               {"console": console_port})
        except gns3api.GNS3ApiException as err:
            if isinstance(err, gns3api.HTTPError) and err.args[0] == 409:
                widget.info(None, "{}: {}"
                            .format(nodes[node_id]['name'], err.args[1]))
            else:
                die("Can't update node information: {}".format(err))
        else:
            if node['console'] != console_port:
                widget.info(None, "{}: Can't update console port, using {}"
                            .format(nodes[node_id]['name'], node['console']))
        console_port += 1
        if console_port > max_port:
            console_port = min_port

try:
    set_console(sys.argv)
except KeyboardInterrupt:
    sys.stderr.write("Aborted\n")
