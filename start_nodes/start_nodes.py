#!/usr/local/bin/python3

"""
start_nodes - start nodes of a project one by one
"""

import os
import sys
import time
import itertools
import gns3api

def start_node_list(api, node_list):
    for i, node in enumerate(node_list):
        if i > 0:
            yield node
        while True:
            compute = api.request('GET', ('/v2/computes', node['compute_id']))
            if compute['cpu_usage_percent'] < 60.0:
                break
            yield node
        print("Starting '{}'".format(node['name']))
        api.request("POST", ("/v2/projects", node['project_id'],
                             'nodes', node['node_id'], 'start'))

def start_nodes(argv):
    """ parse command line, retrieve nodes and start nodes one by one """

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

    # create nodes list per compute
    compute_nodes = {}
    for node_id in sel_nodes:
        node = nodes[node_id]
        if node['status'] != 'started':
            compute_nodes.setdefault(node['compute_id'], []).append(node)

    # iterate through compute_nodes and start them
    print("Starting nodes one by one")
    nodes_iter = [start_node_list(api, node_list)
                  for node_list in compute_nodes.values()]
    try:
        for node in itertools.zip_longest(*nodes_iter):
            time.sleep(4)
    except gns3api.GNS3ApiException as err:
        sys.exit("Can't start node: {}".format(err))


try:
    start_nodes(sys.argv)
except KeyboardInterrupt:
    print()
    sys.exit("Aborted\n")
