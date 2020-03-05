#!/usr/local/bin/python3
"""
Close Project - close GNS3 project
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
    die("usage: close_project version parameter-file project-id [sel-item ...]")
try:
    with open(sys.argv[2], "r") as file:
        cntl_url, cntl_user, cntl_passwd, *_ = file.read(512).splitlines()
    if sys.argv[2].endswith(".tmp"):
        os.remove(sys.argv[2])
except (OSError, ValueError) as err:
    die("Can't get controller connection params: {}".format(err))
project_id = sys.argv[3]

# connect to GNS3 controller
try:
    api = gns3api.GNS3Api(cntl_url, cntl_user, cntl_passwd)
except gns3api.GNS3ApiException as err:
    die("Can't connect to GNS3 controller: {}".format(err))

api.request("POST", ("/v2/projects", project_id, "close"))
