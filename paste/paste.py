#!/usr/local/bin/python3

"""
paste.py - send list of commands one by one to the node
"""

import os
import sys
import telnetlib
import gns3api

def get_console(argv):
    """ parse command line and retrieve console host and port """

    # get arguments
    if len(argv) < 4:
        sys.exit("usage:\npaste version parameter-file project-id [sel-item ...]")
    try:
        with open(argv[2], "r") as file:
            cntl_url, cntl_user, cntl_passwd, *_ = file.read(512).splitlines()
        if argv[2].endswith(".tmp"):
            os.remove(argv[2])
    except (OSError, ValueError) as err:
        sys.exit("Can't get controller connection params: {}".format(err))
    project_id = argv[3]
    sel_nodes = [node[6:] for node in argv[4:] if node.startswith("nodes/")]
    if not sel_nodes:
        sys.exit("No node selected")
    elif len(sel_nodes) != 1:
        sys.exit("Select only one node")
    node_id = sel_nodes[0]

    # connect to GNS3 controller
    try:
        api = gns3api.GNS3Api(cntl_url, cntl_user, cntl_passwd)
    except gns3api.GNS3ApiException as err:
        sys.exit("Can't connect to GNS3 controller: {}".format(err))

    try:
        node = api.request('GET', ('/v2/projects', project_id, 'nodes', node_id))
        node_name = node['name']
        if node['status'] != 'started':
            sys.exit("Node '{}' is {}".format(node_name, node['status']))

        console_port = node['console']
        if not console_port:
            sys.exit("Node '{}' doesn't use the console".format(node_name))
        console_host = node['console_host']
        if console_host in ('0.0.0.0', '::'):
            compute = api.request('GET', ('/v2/computes', node['compute_id']))
            console_host = compute['host']
    except gns3api.GNS3ApiException as err:
        sys.exit("Can't get node information: {}".format(err))

    return (node_name, console_host, console_port)

def send_commands(node_name, console_host, console_port):
    """ read commands from stdin and send them to the node """

    stdin_bin = sys.stdin.buffer
    stdout_bin = sys.stdout.buffer

    prompt = b'[>#] ?$'
    status = "???"

    try:

        # open telnet connection
        status = "connect"
        telnet = telnetlib.Telnet(console_host, console_port, 10)

        # read old junk
        while telnet.read_until(b'xyzzy', timeout=0.3):
            pass

        # send a <CR>
        status = "first contact"
        telnet.write(b'\r')		# first <return>
        try:
            telnet.expect([prompt], 5)
        except OSError:
            pass
        telnet.write(b'\r')		# second <return>
        (_, _, data) = telnet.expect([prompt], 5)
        data = data.splitlines()[-1]

        # get commands
        status = "getting commands"
        print("Paste commands, end with EOF...")
        commands = stdin_bin.readlines()
        print('')

        # send commands
        status = "sending commands"
        stdout_bin.write(data)
        stdout_bin.flush()
        for line in commands:
            line = line.rstrip(b'\r\n')
            while True:
                data = telnet.read_until(b'xyzzy', timeout=0.2)
                if not data:
                    break
                stdout_bin.write(data)
                stdout_bin.flush()
            telnet.write(line + b'\r')
            (_, _, data) = telnet.expect([prompt], 5)
            stdout_bin.write(data)
            stdout_bin.flush()

        # close connection
        status = "close"
        telnet.close()
        print('')

    except OSError as err:
        sys.exit("\n{}: I/O error during {} - {}\n".format(node_name, status, err))
    except KeyboardInterrupt:
        telnet.close()
        sys.exit("\n{}: Aborted\n".format(node_name))


if __name__ == "__main__":
    send_commands(*get_console(sys.argv))
