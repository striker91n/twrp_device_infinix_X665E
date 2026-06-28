# Research Notes: Infinix X665E (Hot 20i) — TWRP Build

## How Recovery-as-Boot Works (BOARD_USES_RECOVERY_AS_BOOT = true)

- boot.img (same partition for both boot_a/boot_b) contains kernel + unified ramdisk
- Ramdisk can boot Android OR recovery depending on `androidboot.force_normal_boot=1` kernel cmdline
- LK always loads boot.img from current active slot
- Normal boot: LK adds `androidboot.force_normal_boot=1` → init chainloads /system/bin/init → Android
- Recovery boot (Vol Up+Power / BCB): LK OMITS `force_normal_boot=1` → init stays in recovery → TWRP/stock recovery
- TWRP's init (via ForceNormalBoot()) handles this: if flag present → boot Android, if absent → show TWRP UI
- "No command" screen is stock recovery's security splash — bypass with Power+Vol Up tap

## BCB (Bootloader Control Block)

- Lives in `misc` partition → on MTK = `/dev/block/by-name/para` (confirmed from recovery.log)
- Structure: struct bootloader_message { char command[32]; char status[32]; char recovery[768]; char stage[32]; }
- Commands: "boot-recovery" (enter recovery mode), "boot-fastboot" (enter fastbootd), "bootonce-bootloader" (enter LK fastboot)
- `adb reboot recovery` writes "boot-recovery" to BCB in `para` partition, then reboots
- LK reads BCB, sees command, loads boot.img accordingly with/without force_normal_boot

## Stock Recovery Behavior (from user testing)

- Vol Up + Power → enters recovery mode from current slot's boot.img
- Recovery menu options: "Boot to bootloader", "Enter fastboot", "View recovery log"
- Stock recovery ADB is UNAVAILABLE (user build, adbd not started)
- Recovery log at /tmp/recovery.log (39KB)

## Recovery.log Part 1 Findings (June 28, 2026)

Recovery log key entries:
- `Boot command: bootonce-bootloader` — confirms BCB read from `para` partition
- Partition table (MTK standard):
  - misc → /dev/block/by-name/para  (BCB lives here)
  - boot_para → /dev/block/by-name/boot_para  (A/B slot metadata)
  - boot → /dev/block/by-name/boot_a
  - No separate recovery partition (recovery is inside boot.img)
- Display: 720×1610, 32-bit framebuffer (fb0)
- MTK-specific partitions: tranfs, boot_para, gz1/gz2, sspm_1/sspm_2, scp1/scp2, tee1/tee2

## ForceNormalBoot Verified (June 28, 2026)

Normal boot `/proc/cmdline`:
- `androidboot.force_normal_boot=1` ← PRESENT
- `androidboot.slot_suffix=_a`
- `androidboot.bootreason=reboot`
- `androidboot.verifiedbootstate=orange`
- `androidboot.hardware=mt6765` (kernel reports mt6765, ro.boot.hardware=mt6762 — variant)
- `buildvariant=user`

Recovery boot (from recovery.log):
- `androidboot.force_normal_boot=1` ← ABSENT
- `ro.boot.bootreason=rtc`
- `ro.boot.mode=recovery`

Flow confirmed: LK controls `force_normal_boot=1` based on boot mode.
- Normal = present → TWRP init chainloads Android
- Recovery = absent → TWRP init starts TWRP UI

## Recovery.log Part 2 Findings

Confirmed recovery key combo boot flow:
- `ro.boot.mode=recovery` — LK loaded boot.img in recovery mode
- `ro.boot.bootreason=rtc` — RTC bits used (adb reboot recovery or key combo)
- `ro.boot.slot=a` — booted from current active slot (a)
- `ro.boot.flash.locked=0` — bootloader unlocked
- `ro.boot.verifiedbootstate=orange`
- `ro.debuggable=0`, `ro.adb.secure=1` — stock recovery ADB inaccessible
- `ro.boot.boot_devices=bootdevice, soc/11230000.mmc, 11230000.mmc, soc/11230000.msdc, 11230000.msdc`
- `ro.build.version.security_patch=2023-02-01`
- No `androidboot.force_normal_boot=1` present → confirms recovery mode trigger
- BCB: `Boot command: bootonce-bootloader` (from previous session)
- Build: X665E-H6126YZA...-GL-230215V969, Android 12, SDK 31
- Hardware: MT6762 (Helio G25), arm64-v8a
- Display: 720×1610, 32-bit framebuffer

## MTK Preloader Commands

The preloader (first-stage bootloader after BROM) exposes two command interfaces over USB CDC ACM (VID 0x0E8D, PID varies).

### Text Commands (ASCII — after preloader sends "READY")

Send as raw ASCII string over CDC ACM serial. Ack is the reversed/transformed string.

| Send | Ack | Boot Mode |
|------|-----|-----------|
| `FASTBOOT` | `TOOBTSAF` | LK fastboot mode |
| `METAMETA` | `ATEMATEM` | META engineering mode |
| `ADVEMETA` | `ATEMEVDA` | Advanced META mode |
| `FACTFACT` | `TCAFTCAF` | Factory mode |
| `FACTORYM` | `MYROTCAF` | ATE factory test |
| `AT+NBOOT` | `AT+OK` | Normal boot |
| `SWITCHMD` | `DMHCTIWS` | Modem download mode |

Constants from MTK source (`meta.h`):
```c
#define HSHK_COM_READY          "READY"
#define META_STR_REQ            "METAMETA"
#define META_STR_ACK            "ATEMATEM"
#define META_ADV_REQ            "ADVEMETA"
#define META_ADV_ACK            "ATEMEVDA"
#define FACTORY_STR_REQ         "FACTFACT"
#define FACTORY_STR_ACK         "TCAFTCAF"
#define ATE_STR_REQ             "FACTORYM"
#define ATE_STR_ACK             "MYROTCAF"
#define SWITCH_MD_REQ           "SWITCHMD"
#define SWITCH_MD_ACK           "DMHCTIWS"
#define ATCMD_PREFIX            "AT+"
#define ATCMD_NBOOT_REQ         ATCMD_PREFIX"NBOOT"
#define ATCMD_OK                ATCMD_PREFIX"OK"
#define FB_STR_REQ              "FASTBOOT"
#define FB_STR_ACK              "TOOBTSAF"
```

Python usage:
```python
import serial
s = serial.Serial("COMx", 115200, timeout=1)
resp = s.read(5)  # b"READY"
s.write(b"FASTBOOT")
resp = s.read(8)  # b"TOOBTSAF" — device will now re-enumerate as fastboot
```

### Binary Commands (after handshake 0xA0 0x0A 0x50 0x05)

Handshake: host sends each byte, device echoes complement (0xA0→0x5F, 0x0A→0xF5, 0x50→0xAF, 0x05→0xFA).

| Code | Name | Function |
|------|------|----------|
| `0x70` | SEND_PARTITION_DATA | Send raw data to partition |
| `0x71` | JUMP_TO_PARTITION | Jump to named partition |
| `0x72` | CHECK_USB_CMD | Check USB status |
| `0x80` | STAY_STILL | No operation |
| `0x88` | CMD_88 | Unknown |
| `0xA2` | CMD_READ16_A2 | Legacy 16-bit memory read |
| `0xB0` | I2C_INIT | Initialize I2C |
| `0xB1` | I2C_DEINIT | Deinitialize I2C |
| `0xB2` | I2C_WRITE8 | I2C 8-bit write |
| `0xB3` | I2C_READ8 | I2C 8-bit read |
| `0xB4` | I2C_SET_SPEED | Set I2C speed |
| `0xB6`-`0xBA` | I2C_*_EX | Extended I2C commands |
| `0xBF` | GET_MAUI_FW_VER | Get MAUI firmware version |
| `0xC1`-`0xC3` | OLD_SLA_* | Legacy SLA authentication |
| `0xC4` | PWR_INIT | Power management init |
| `0xC5` | PWR_DEINIT | Power management deinit |
| `0xC6` | PWR_READ16 | Read PMIC 16-bit register |
| `0xC7` | PWR_WRITE16 | Write PMIC 16-bit register |
| `0xC8` | CMD_C8 | Cache control / extended cmd trampoline |
| `0xD0` | READ16 | Read 16-bit memory (addr + dwords) |
| `0xD1` | READ32 | Read 32-bit memory (addr + dwords) |
| `0xD2` | WRITE16 | Write 16-bit values |
| `0xD3` | WRITE16_NO_ECHO | Write 16-bit without echo ack |
| `0xD4` | WRITE32 | Write 32-bit values |
| `0xD5` | **JUMP_DA** | Jump to Download Agent at addr |
| `0xD6` | JUMP_BL | Jump to bootloader (continue boot) |
| `0xD7` | **SEND_DA** | Send Download Agent binary to addr |
| `0xD8` | GET_TARGET_CONFIG | Get security config flags (SBC/SLA/DAA/etc) |
| `0xD9` | SEND_ENV_PREPARE | Send environment prepare data |
| `0xDA` | brom_register_access | Direct BROM register access (exploit) |
| `0xDB` | UART1_LOG_EN | Enable UART logging |
| `0xDC` | UART1_SET_BAUDRATE | Set UART baud rate |
| `0xDD` | BROM_DEBUGLOG | Get BROM debug log |
| `0xDE` | JUMP_DA64 | Jump to 64-bit DA |
| `0xDF` | GET_BROM_LOG_NEW | Get BROM log (new format) |
| `0xE0` | SEND_CERT | Send root certificate |
| `0xE1` | GET_ME_ID | Get MediaTek chip ID |
| `0xE2` | SEND_AUTH | Send authentication blob |
| `0xE3` | SLA | SLA challenge-response |
| `0xE4` | CMD_E4 | Unknown (returns 0x703A) |
| `0xE5` | CMD_E5 | Echo dword (returns 0x7054) |
| `0xE6` | CMD_E6 | Unknown (returns 0x7054) |
| `0xE7` | GET_SOC_ID | Get SoC identifier |
| `0xE8` | CMD_E8 | Certificate check (returns 0x100A00) |
| `0xF0` | ZEROIZATION | Zeroization command |
| `0xFA` | CMD_FA | Unknown |
| `0xFB` | GET_PL_CAP | Get preloader capabilities |
| `0xFC` | GET_HW_SW_VER | Get HW/SW version |
| `0xFD` | GET_HW_CODE | Get hardware code |
| `0xFE` | GET_BL_VER | Get bootloader version |
| `0xFF` | GET_VERSION | Get BROM version |

### Bypassing LK (SEND_DA + JUMP_DA)

The preloader can load and execute arbitrary code without LK:
1. `SEND_DA` (0xD7): upload a Download Agent binary to memory
2. `JUMP_DA` (0xD5): jump to execute it
3. The DA handles DRAM init and can load further payloads

This is how SP Flash Tool, mtkclient, etc. flash devices. On this device, DAA (Download Agent Authorization) status was reported as True in forum posts — meaning it might reject unsigned DAs. Tested crash exploit (kamakiri) didn't work, suggesting security patches are applied.

### Target Config Flags (from GET_TARGET_CONFIG, 0xD8)

4-byte bitmask:
| Bit | Flag | Description |
|-----|------|-------------|
| 0 | SBC | Secure Boot Control |
| 1 | SLA | Security Lifecycle Assurance |
| 2 | DAA | Download Agent Authentication |
| 3 | SWJTAG | Software JTAG enabled |
| 4 | EPP | EPP_PARAM at 0x600 |
| 5 | CERT | Root certificate required |
| 6 | MEMREAD | Memory read requires auth |
| 7 | MEMWRITE | Memory write requires auth |
| 8 | CMDC8 | Command 0xC8 blocked |

### BROM Mode / Test Points

- `androidboot.blow_disbrom=0` — BROM USB download NOT permanently disabled
- BROM accessible via test point shorting (disassemble required)
- Test point images available at: romprovider.com, fidetec.com, serviceemmc.com for X665E
- General procedure: short test point contacts with tweezers → connect USB → device appears as BROM COM port
- Bypasses preloader entirely; useful if preloader/LK both corrupted

### Key Takeaway for TWRP Work

We don't need any of these. We have:
1. Fastboot access via `FASTBOOT` text command to preloader OR "Boot to bootloader" in recovery
2. Recovery mode via Vol Up + Power
3. Working `fastboot flash boot_a` for flashing TWRP
4. BROM test points as absolute last resort only if LK/preloader are both bricked (which our operation cannot cause)

## Key Partitions

| Mount Point | Partition | Block Device |
|-------------|-----------|--------------|
| /system     | system_a  | (dynamic)    |
| /vendor     | vendor_a  | (dynamic)    |
| /product    | product_a | (dynamic)    |
| /boot       | boot_a    | /dev/block/by-name/boot_a |
| /misc       | para      | /dev/block/by-name/para   |
| boot_para   | boot_para | /dev/block/by-name/boot_para |
| /data       | userdata  | /dev/block/by-name/userdata |
| /metadata   | md_udc    | /dev/block/by-name/md_udc |

## A/B Slots

- boot_a + boot_b (both 32MB / 0x2000000)
- system_a/system_b, vendor_a/vendor_b, product_a/product_b (dynamic inside super)
- Active slot stored in boot_para partition
- `fastboot --set-active=_b` writes to boot_para
- On MTK, `boot_para` stores slot metadata (not misc/para)

## PC-Free TWRP Access Plan

1. Flash TWRP to boot_a (replaces stock boot.img)
2. Power on normally: LK passes force_normal_boot=1 → TWRP init detects it → boots Android
3. Vol Up + Power (recovery key combo): LK omits force_normal_boot=1 → TWRP init stays → TWRP UI
4. No slot switching needed — TWRP and Android coexist on same partition
5. After initial flash via PC (fastboot), user can access TWRP anytime via key combo

## MTK LK Boot Modes

- NORMAL_BOOT(0): loads boot.img with force_normal_boot=1
- RECOVERY_BOOT(2): loads boot.img WITHOUT force_normal_boot=1 (or from PART_RECOVERY on old devices)
- FASTBOOT(99): enters LK fastboot mode
- Boot mode determined by: RTC bits (adb reboot), BCB (para partition), key combos

## Key Combos (Infinix X665E)

- Recovery: Vol Up + Power (at boot, release power at logo, keep vol up)
- Fastboot: From recovery menu → "Boot to bootloader" OR `adb reboot bootloader`
- Fastbootd: From recovery menu → "Enter fastboot"
