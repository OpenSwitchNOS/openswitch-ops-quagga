OPS-ZEBRA
=========

What is ops-zebra?
----------------
ops-zebra in [OpenSwitch](http://www.openswitch.net), is a module that is responsible for getting routes configurations from UI and Protocols and configuring the best static and protocol routes into kernel, which are then used in slowpath routing by kernel.

ops-zebra is heavily based on project quagga (https://github.com/opensourcerouting/quagga) and will be frequently upstreaming its changes to the parent project.

What is the structure of the repository?
----------------------------------------
* zebra source file are under this subdirectory.
* ../ops/test - contain all the component tests of ops-zebra based on ops mininet framework.
* ../ops-quagga/ - contains the modified quagga project sources.

What is the license?
--------------------
Being heavily based on project bar, ops-zebra inherits its GNU GPL 2.0 license or any later version (https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html). For more details refer to COPYING file.

What other documents are available?
----------------------------------
For the high level design of ops-zebra, refer to [DESIGN.md](DESIGN.md)
For answers to common questions, read [FAQ.md](FAQ.md)
For the current list of contributors and maintainers, refer to [AUTHORS.md](AUTHORS.md)
For general information about OpenSwitch project refer to http://www.openswitch.net
