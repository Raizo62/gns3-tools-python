#!/usr/local/bin/python3

"""
nodes_log - get log of nodes
"""

import os
import sys
import gns3api

def node_file(api, node, fname):
    """ get file from a node """
    data = None
    try:
        data = api.request("GET", ("/v2/projects", node['project_id'],
                                   "nodes", node['node_id'], "files", fname))
    except gns3api.GNS3ApiException as err:
        if api.status_code != 404:
            sys.exit("Can't get log file: {}".format(err))

    if data:
        data = fname + ":\n" + \
               data.decode('utf-8', errors='ignore').rstrip("\n") + "\n\n"
    else:
        data = ""
    return data

def nodes_log(argv):
    """ parse command line, retrieve nodes and get log of nodes """

    # get arguments
    if len(argv) < 4:
        sys.exit("usage:\nstart_nodes version parameter-file project-id [sel-item ...]")
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
        sys.exit("Can't connect to GNS3 controller: {}".format(err))

    # get node information
    nodes = {}
    try:
        for node in api.request('GET', ('/v2/projects', project_id, 'nodes')):
            nodes[node['node_id']] = node
    except gns3api.GNS3ApiException as err:
        sys.exit("Can't get node information: {}".format(err))
    if not nodes:
        sys.exit("No node in project")

    # get selected nodes
    if not sel_items:
        sel_nodes = list(nodes.keys())
    else:
        sel_nodes = [item[6:] for item in sel_items
                     if item.startswith("nodes/")]
        if not sel_nodes:
            sys.exit("No node selected")

    sel_nodes.sort(key=lambda k: nodes[k]['name'].lower())

    # get log of nodes
    log = ""
    for node_id in sel_nodes:
        node = nodes[node_id]
        log += "*** {} ({})\n\n".format(node['name'], node['node_id'])
        if node['node_type'] == 'docker':
            log += node_file(api, node, "vnc.log")
        elif node['node_type'] == 'dynamips':
            log += node_file(api, node,
                             "{}_i{}_log.txt".format(
                                 node['properties']['platform'],
                                 node['properties']['dynamips_id']))
        elif node['node_type'] == 'qemu':
            log += node_file(api, node, "qemu.log")
            log += node_file(api, node, "qemu-img.log")
        elif node['node_type'] == 'vpcs':
            log += node_file(api, node, "vpcs.log")
        log += node_file(api, node, "ubridge.log")

    sys.stdout.write(log)


try:
    nodes_log(sys.argv)
except KeyboardInterrupt:
    print()
    sys.exit("Aborted\n")
