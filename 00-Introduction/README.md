# OpenShift introduction

## What is OKD?

[OKD](https://okd.io/docs/project/about/) is the open-source community
distribution of Kubernetes associated with Red Hat OpenShift. Formerly known
as **OpenShift Origin**, its name has also been expanded as **Origin Community
Distribution of Kubernetes**.

- **Community project:** OKD brings together Kubernetes and tools for developing,
  deploying, and managing containerized applications.
- **Relationship to OpenShift:** OKD and Red Hat OpenShift Container Platform
  share many technologies. The project describes them as sibling distributions;
  OpenShift Container Platform provides Red Hat's commercial support.
- **Developer tools:** A built-in web console and Source-to-Image (S2I) builds
  help developers turn application source code into running containers.

See the [OKD project overview](https://okd.io/docs/project/) and
[official documentation](https://docs.okd.io/) for more details.

## Index

1. [00 - Bash configuration](../00-bashrc.md): `.bashrc` additions and validation; apply after installing CRC.
2. [00 - Installation](00-Installation.md)
3. [01 - CRC commands](01-CRC-Commands.md)
4. [02 - OpenShift oc commands](02-OC-Commands.md)
5. [03 - Architecture](03-Architecture.md)

## Training guides

Read [`00-Installation.md`](00-Installation.md) and run its fenced Bash blocks in the VM terminal. Use [00-bashrc.md](../00-bashrc.md) for the three `.bashrc` additions and three validation stages. Back up your existing `~/.bashrc` before applying the additions.


Read [`03-Architecture.md`](03-Architecture.md) for the illustrated guide covering the stack, pods, containers, storage, databases and CRC system services. Diagram sources and PNG/SVG assets are in `assets/`; rebuild them with `python assets/build_architecture.py` (Pillow required).


Run selected command blocks in the Linux VM terminal. Deletion and cleanup examples are commented out with `#` to avoid accidental execution. Do not uncomment or run them.

Next: [01 - Getting started](../01-GetStarted/README.md).
