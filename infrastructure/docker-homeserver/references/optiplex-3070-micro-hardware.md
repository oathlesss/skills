# OptiPlex 3070 Micro — Hardware Reference

Ruben's homeserver machine. Confirmed specs from sysfs/lspci/DMI inspection + cross-referenced with Dell's service manual.

## Machine Identity

| Field | Value |
|---|---|
| **Model** | Dell OptiPlex 3070 |
| **Form factor** | Micro (1-liter mini PC, 182×178×36mm) |
| **Motherboard** | 02N3WF Rev A01 |
| **SKU** | 0930 |
| **CPU** | Intel i5-9500T (6C/6T, 2.20 GHz base) |
| **RAM** | 32 GB DDR4 |
| **BIOS** | Dell Inc. v1.35.0 (2025-09-04) |

## Storage — What's Present

| Slot | Type | Speed | Current Drive |
|---|---|---|---|
| **M.2 2280** (occupied) | NVMe PCIe 3.0 x4 | 5.0 GT/s × 4 lanes = ~3.5 GB/s | KIOXIA KBG50ZNS256G (256GB, DRAM-less) |
| **2.5" SATA bay** | SATA III (AHCI) | 6 Gbps = ~550 MB/s | **Empty** — bay exists, caddy + cable not installed |
| **USB 3.1 Gen 2** | Type-C + Type-A | 10 Gbps = ~1000 MB/s | External only |

## The 2.5" Bay — Confirmed ✅

Multiple authoritative sources confirm the 3070 Micro has an internal 2.5" bay:
- **Dell Service Manual** — section titled "Installing the 2.5-inch hard drive into the drive bracket" for the 3070 Micro
- **Dell Spec Sheet** — *"2.5 Inch Solid State Drives are only available as a secondary storage"*
- **Dell Community Forum** (May 2024) — *"The OptiPlex 3070 micro can support one 2.5" HDD/SSD and one M.2 SATA/NVMe SSD"*
- **iFixit** — full repair guide: "Dell OptiPlex 3070 Micro-PC Hard Drive Replacement"

The Intel Cannon Lake AHCI SATA controller (PCI 00:17.0) exposes 5 ports in sysfs (`ata1`–`ata5`). All show no connected devices — the SATA controller is present and ready, just needs the caddy + cable + drive.

## Parts to Add a 2.5" SATA SSD

| Part | Dell P/N | Notes |
|---|---|---|
| **2.5" HDD Caddy/Bracket** | **JMYPN** (0JMYPN) | Plastic sled. Same across Micro line: 3040/3050/3060/3070/5040/5050/5060/5070/7040/7050/7060/7070. ~$8–12 on Amazon, $5–10 on eBay. |
| **SATA Combo Cable** | **6J3FV** (CPX-6J3FV) | Combined SATA data+power. Dell-listed compatible with 3070 Micro. ~$10 on Dell.com or eBay. |

## SATA Controller Detection (Linux)

```bash
# SATA controller present
lspci | grep -i sata
# → 00:17.0 SATA controller: Intel Corporation Cannon Lake PCH SATA AHCI Controller

# Ports visible
ls /sys/class/ata_port/
# → ata1 ata2 ata3 ata4 ata5

# No drives connected
ls /sys/class/ata_device/
# → dev1.0 dev2.0 dev3.0 dev4.0 dev5.0  (all show "unknown" class, no link speed)
```

## USB Ports

```
Bus 001: 480M  (USB 2.0, 16 ports)  — internal Bluetooth on port 14
Bus 002: 10000M (USB 3.1 Gen 2, 8 ports) — all external
```

## NVMe Drive Details

```
Model:  KBG50ZNS256G NVMe KIOXIA 256GB
Firmware: 11200109
Sector size: 512 bytes
Total sectors: 500,118,192 (~256 GB)
PCIe link: 5.0 GT/s × 4 lanes (Gen 3 x4)
Controller: BG5 (DRAM-less)
```

## Current Disk Layout

```
nvme0n1       238.5G
├─nvme0n1p1     1G  /boot/efi  (vfat)
└─nvme0n1p2 237.4G  /          (ext4, 20G used / 202G free)
```

No SATA devices (`/dev/sda` does not exist). No USB storage attached.

## Docker & Service Data Usage

| Path | Size |
|---|---|
| `/home/ruben/homeserver/` (total) | 1.5 GB |
| `/home/ruben/homeserver/minecraft/data` | 301 MB |
| `/home/ruben/homeserver/couchdb/data` | 224 KB |
| `/home/ruben/homeserver/tailscale/state` | 36 KB |
| `/home/ruben/homeserver/caddy/data` | 8 KB |
| Docker images total | 5 GB (6 active images) |
| `/home/ruben/project-arachne/` | 3.1 MB |
| `/home/ruben/obsidian-vault/` | 188 KB |

## Planned Upgrade Path

See vault note: `inbox/OptiPlex 3070 Micro Storage Upgrade Options.md`
- Phase 1: 2TB 2.5" SATA SSD + JMYPN caddy + 6J3FV cable, mount as `/data`
- Phase 2 (future): replace 256GB NVMe with 1TB when OS/Docker outgrow it
