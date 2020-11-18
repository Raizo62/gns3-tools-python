# GNS3 Tools

This is my collection of tools, integrated into the GNS3 GUI, see
<https://www.b-ehlers.de/blog/posts/2018-01-12-gns3-integrate-programs/>
for details.
These tools are licensed under the GPLv3 license.

## Prerequisites

- Python 3 installed
- [gns3-gui-tools](https://git.b-ehlers.de/ehlers/gns3-gui-tools)
  integrated into GNS3.
- [gns3api](https://git.b-ehlers.de/ehlers/gns3api-python)
  installed or copied to the GNS3/tools folder.
- The simple widget modules qt_widgets.py and tk_widgets.py
  copied to the GNS3/tools folder.

## Tools

- adapter_count   - change the number of adapters
- close_project   - close current GNS3 project
- console_port    - change console port of one or more nodes
- export_template - export template as GNS3 appliance
- link_resume     - resume links of all/selected nodes
- nodes_log       - get log of nodes
- paste           - send list of commands one by one to a cisco/juniper node
- start_nodes     - start nodes of a project one by one

Copy the desired tools and their accompanied .json files to the
GNS3/tools folder, then restart the GNS3 GUI.
