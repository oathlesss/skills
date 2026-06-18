# Linux Hardware Inspection Without Sudo

When `sudo` is unavailable and tools like `lshw`, `dmidecode`, or `nvme-cli` aren't installed, sysfs and proc expose everything needed. These commands work unprivileged.

## NVMe Drive Info (no nvme-cli, no sudo)

```bash
# Drive model
cat /sys/class/nvme/nvme0/model                    # e.g. "KBG50ZNS256G NVMe KIOXIA 256GB"

# Firmware
cat /sys/class/nvme/nvme0/firmware_rev             # e.g. "11200109"

# Sector size (in bytes)
cat /sys/block/nvme0n1/queue/physical_block_size   # usually 512

# Total sectors (capacity)
cat /sys/block/nvme0n1/size                        # multiply by 512 for bytes

# PCIe link speed (e.g. "5.0 GT/s PCIe" = Gen 3)
cat /sys/class/nvme/nvme0/device/current_link_speed

# PCIe link width (e.g. "4" = x4 lanes)
cat /sys/class/nvme/nvme0/device/current_link_width

# PCIe generation mapping:
# 2.5 GT/s = Gen 1,  5.0 GT/s = Gen 2,  8.0 GT/s = Gen 3,  16.0 GT/s = Gen 4
```

## SATA Controller & Ports (no sudo)

```bash
# Find SATA controller
lspci | grep -i "SATA\|AHCI"

# List SATA ports (presence doesn't mean a drive is connected)
ls /sys/class/ata_port/          # ata1, ata2, ...

# Check if a drive is connected to a port (non-empty = drive present)
ls /sys/class/ata_device/
# Connected ports have entries like dev1.0

# Check link speed (only populated when drive is connected)
cat /sys/class/ata_link/link1/sata_spd   # e.g. "3.0 Gbps" or "<unknown>" if empty
```

## USB Controller & Ports

```bash
# USB hierarchy with speeds — bus-level view
lsusb -t
# Example output:
# Bus 001: 480M (USB 2.0, 60 MB/s)
# Bus 002: 10000M (USB 3.1 Gen 2, 10 Gbps)

# List connected devices
lsusb

# Speed mapping:
# 480M   = USB 2.0 High Speed (60 MB/s)
# 5000M  = USB 3.0 / 3.1 Gen 1 (5 Gbps, ~500 MB/s)
# 10000M = USB 3.1 Gen 2 (10 Gbps, ~1000 MB/s)
```

## Storage Controllers (lspci, no sudo needed)

```bash
# All storage controllers
lspci | grep -iE "storage|sata|nvme"

# Get driver in use for a specific device
lspci -k -s 03:00.0 | grep "Kernel driver"
```

## Motherboard & System Info (sysfs DMI, no sudo/dmidecode)

```bash
# Motherboard model
cat /sys/devices/virtual/dmi/id/board_name       # e.g. "02N3WF"
cat /sys/devices/virtual/dmi/id/board_version    # e.g. "A01"

# System vendor/product
cat /sys/devices/virtual/dmi/id/sys_vendor       # e.g. "Dell Inc."
cat /sys/devices/virtual/dmi/id/product_name     # e.g. "OptiPlex 3070"

# BIOS version
cat /sys/devices/virtual/dmi/id/bios_version
```

## CPU & Memory (procfs)

```bash
# CPU model
grep "model name" /proc/cpuinfo | head -1

# Total memory
grep MemTotal /proc/meminfo

# Available memory (what the kernel can give without swapping)
grep MemAvailable /proc/meminfo
```

## Disk Layout (no sudo)

```bash
# Block device tree with sizes, types, mountpoints
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE

# Filesystem usage
df -h

# fstab (how drives are mounted at boot)
cat /etc/fstab
```

## Kernel Detection Messages (dmesg, no sudo needed on most distros)

```bash
# Storage-related boot messages
dmesg | grep -iE "ahci|sata|nvme|scsi" | head -20

# Check for any errors or detection failures
dmesg | grep -i "link down\|failed\|error" | grep -i "ata\|nvme"
```

## Docker Storage Usage

```bash
# Summary
docker system df

# Detailed breakdown (images, containers, volumes, build cache)
docker system df -v

# Docker root directory
docker info | grep "Docker Root Dir"

# List bind mounts for running containers
docker inspect $(docker ps -q) --format '{{.Name}} {{range .Mounts}}{{if eq .Type "bind"}}{{.Source}} -> {{.Destination}} {{end}}{{end}}'
```

## Directory Usage (Find What's Eating Space)

```bash
# Top-level directories on root
du -sh /* 2>/dev/null | sort -rh | head -15

# Docker home directory
du -sh /home/*/ 2>/dev/null | sort -rh | head -10

# Specific Docker service data
du -sh /home/ruben/homeserver/*/data /home/ruben/homeserver/*/world 2>/dev/null | sort -rh
```

## Complete One-Shot Hardware Summary

```bash
echo "=== CPU ===" && grep "model name" /proc/cpuinfo | head -1
echo "=== RAM ===" && grep -E "MemTotal|MemAvailable" /proc/meminfo
echo "=== BOARD ===" && cat /sys/devices/virtual/dmi/id/product_name && cat /sys/devices/virtual/dmi/id/board_name
echo "=== NVMe ===" && cat /sys/class/nvme/nvme0/model 2>/dev/null && cat /sys/class/nvme/nvme0/device/current_link_speed 2>/dev/null && echo "x$(cat /sys/class/nvme/nvme0/device/current_link_width 2>/dev/null)"
echo "=== SATA ===" && lspci | grep -i sata && ls /sys/class/ata_device/ 2>/dev/null
echo "=== USB ===" && lsusb -t 2>/dev/null | grep -E "^/:|10000M|5000M|480M"
echo "=== DISKS ===" && lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE
echo "=== SPACE ===" && df -h /
echo "=== DOCKER ===" && docker system df 2>/dev/null
```
