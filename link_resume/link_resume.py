#!/usr/local/bin/python3

"""
link_resume.py - resume links of all/selected nodes
"""

import os
import sys
import gns3api
from qt_widgets import SimpleWidgets

def die(text):
    """ terminate program with error message """
    SimpleWidgets().alert(None, text)
    sys.exit(text)


def link_resume(argv):
    """ parse command line, retrieve nodes and resume connected links """

    # get arguments
    if len(argv) < 4:
        die("usage:\nlink_resume version parameter-file project-id [sel-item ...]")
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

    try:
        if not sel_items:
            # resume all links
            for link in api.request('GET', ('/v2/projects', project_id, 'links')):
                if link['suspend']:
                    api.request('PUT', ('/v2/projects', project_id, 'links', link['link_id']),
                                {'suspend': False})
        else:
            # resume links of selected nodes
            sel_nodes = frozenset(item[6:] for item in sel_items
                                  if item.startswith("nodes/"))
            if not sel_nodes:
                die("No node selected")
            for link in api.request('GET', ('/v2/projects', project_id, 'links')):
                if not link['suspend']:
                    continue
                for node in link['nodes']:
                    if node['node_id'] in sel_nodes:
                        api.request('PUT', ('/v2/projects', project_id, 'links', link['link_id']),
                                    {'suspend': False})
                        break
    except gns3api.GNS3ApiException as err:
        die("Can't get/set link information: {}".format(err))

try:
    link_resume(sys.argv)
except KeyboardInterrupt:
    sys.stderr.write("Aborted\n")
