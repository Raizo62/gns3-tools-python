#!/usr/local/bin/python3

"""
start_nodes - start nodes of a project one by one
"""

import os
import sys
import time
import gns3api

def start_node_list(api, node_list):
    """ start nodes, yield sleeps the specified number of seconds """
    delay_next_node = 0
    for node in node_list:
        if delay_next_node > 0:		# delay between starting nodes
            yield delay_next_node
        while True:
            compute = api.request('GET', ('/v2/computes', node['compute_id']))
            if compute['cpu_usage_percent'] < 60.0:
                break
            yield 4			# test again in 4 seconds
        print("Starting '{}'".format(node['name']))
        api.request("POST", ("/v2/projects", node['project_id'],
                             'nodes', node['node_id'], 'start'))
        if node['node_type'] in ("qemu", "virtualbox", "vmware"):
            delay_next_node = 4
        else:
            delay_next_node = 2

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
    tasks = {compute_id: {
                'iter': start_node_list(api, compute_nodes[compute_id]),
                'delay': 0}
             for compute_id in compute_nodes}
    while tasks:
        delay = min([tasks[compute_id]['delay'] for compute_id in tasks])
        if delay > 0.09:
            time.sleep(delay)
        for compute_id in list(tasks.keys()):
            tasks[compute_id]['delay'] -= delay
            if tasks[compute_id]['delay'] <= 0.09:
                try:
                    tasks[compute_id]['delay'] = \
                        max(0, next(tasks[compute_id]['iter']))
                except StopIteration:
                    del tasks[compute_id]
                except gns3api.GNS3ApiException as err:
                    sys.exit("Can't start node: {}".format(err))


try:
    start_nodes(sys.argv)
except KeyboardInterrupt:
    print()
    sys.exit("Aborted\n")
