OPS-ZEBRA
=========

What is ops-zebra?
----------------
The ops-zebra module in [OpenSwitch](http://www.openswitch.net), is responsible for getting route configurations from the management interface and the protocol daemons and configuring the best routes in the kernel. These configurations are then used for slowpath routing in the kernel.

The ops-zebra module is based on project quagga (http://www.nongnu.org/quagga) and is frequently upstreaming its changes to the parent project.

What is the structure of the repository?
----------------------------------------
* The ops-zebra source files are in ops-quagga/zebra.
* The ops-quagga/ops/test/ contain all the component tests of ops-zebra based on ops mininet framework.
* The ops-quagga/ contains the quagga project sources.

What is the license?
--------------------
The ops-zebra module inherits its GNU GPL 2.0 or later (https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html).
For more details refer to COPYING file.

What other documents are available?
----------------------------------
For the high level design of ops-zebra, refer to [DESIGN.md](DESIGN.md)
For answers to common questions, refer to [FAQ.md](FAQ.md)
For the current list of contributors and maintainers, refer to [AUTHORS.md](AUTHORS.md)
For general information about the OpenSwitch project, refer to http://www.openswitch.net
