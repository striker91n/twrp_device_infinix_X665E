import struct
import os
import sys

DT_TABLE_MAGIC = 0xD7B7AB1E
FDT_MAGIC = 0xD00DFEED
MKDTIMG_HEADER_SIZE = 32
MKDTIMG_ENTRY_SIZE = 32

def page_align(size, page_size):
    return ((size + page_size - 1) // page_size) * page_size

def make_mkdtimg(fdt_data, page_size=2048):
    fdt_size = len(fdt_data)
    dt_offset = MKDTIMG_HEADER_SIZE + MKDTIMG_ENTRY_SIZE
    total_size = dt_offset + fdt_size

    hdr = struct.pack('<IIIIIIII',
        DT_TABLE_MAGIC,
        total_size,
        MKDTIMG_HEADER_SIZE,
        MKDTIMG_ENTRY_SIZE,
        1,
        MKDTIMG_HEADER_SIZE,
        page_size,
        0
    )
    entry = struct.pack('<IIIIIIII',
        fdt_size,
        dt_offset,
        0, 0,
        0, 0, 0, 0
    )
    return hdr + entry + fdt_data

def fix_bootimg(input_path, dtb_path, output_path, target_size=33554432):
    with open(input_path, 'rb') as f:
        data = f.read()

    magic = data[:8]
    if magic != b'ANDROID!':
        print(f"ERROR: Not a valid boot image (magic={magic.hex()})")
        return False

    kernel_size = struct.unpack_from('<I', data, 8)[0]
    ramdisk_size = struct.unpack_from('<I', data, 16)[0]
    page_size = struct.unpack_from('<I', data, 36)[0]
    header_version = struct.unpack_from('<I', data, 40)[0] if len(data) >= 44 else 0

    print(f"Kernel size: {kernel_size}")
    print(f"Ramdisk size: {ramdisk_size}")
    print(f"Page size: {page_size}")
    print(f"Header version: {header_version}")

    header_size = page_size

    kernel_offset = header_size
    kernel_padded = page_align(kernel_size, page_size)
    ramdisk_offset = kernel_offset + kernel_padded
    ramdisk_padded = page_align(ramdisk_size, page_size)

    dtb_data_start = ramdisk_offset + ramdisk_padded
    dtb_size = len(data) - dtb_data_start

    if dtb_size <= 0:
        print("ERROR: No DTB area found")
        return False

    print(f"Existing DTB area: offset={dtb_data_start}, size={dtb_size}")
    existing_magic = struct.unpack_from('>I', data, dtb_data_start)[0] if dtb_size >= 4 else 0
    print(f"Existing DTB magic: 0x{existing_magic:08X} {'(MKDTIMG)' if existing_magic == DT_TABLE_MAGIC else '(FDT)' if existing_magic == FDT_MAGIC else '(unknown)'}")

    with open(dtb_path, 'rb') as f:
        dtb_data = f.read()
    print(f"Input DTB size: {len(dtb_data)}")

    input_magic = struct.unpack('>I', dtb_data[:4])[0]
    if input_magic == FDT_MAGIC:
        print("Input is raw FDT, wrapping in MKDTIMG container")
        mkdtimg = make_mkdtimg(dtb_data, page_size)
    elif input_magic == DT_TABLE_MAGIC:
        print("Input is already MKDTIMG, using as-is")
        mkdtimg = dtb_data
    else:
        print(f"ERROR: Unknown DTB format (magic=0x{input_magic:08X})")
        return False

    print(f"Final MKDTIMG size: {len(mkdtimg)}")

    new_dtb_padded = page_align(len(mkdtimg), page_size)
    new_size = dtb_data_start + new_dtb_padded

    if new_size > target_size:
        print(f"ERROR: Image too large ({new_size} > {target_size})")
        return False

    result = bytearray(target_size)
    result[:dtb_data_start] = data[:dtb_data_start]
    result[dtb_data_start:dtb_data_start + len(mkdtimg)] = mkdtimg

    if header_version >= 2 and len(data) >= 1648:
        struct.pack_into('<I', result, 1640, 0)
        struct.pack_into('<I', result, 1644, 0)
    if header_version >= 2 and len(data) >= 1660:
        # Stock image has dtb_size=0 dtb_addr=0 — LK finds MKDTIMG by scanning.
        # Setting these confuses some LK versions. Zero them out like stock.
        struct.pack_into('<I', result, 1648, 0)
        struct.pack_into('<Q', result, 1652, 0)

    with open(output_path, 'wb') as f:
        f.write(result)

    print(f"Wrote {output_path} ({len(result)} bytes)")
    print(f"Content: header={header_size}, kernel={kernel_padded}, ramdisk={ramdisk_padded}, dtb={new_dtb_padded}, total_data={new_size}")
    return True

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python fix_bootimg.py <input_boot.img> <dtb_file> [output]")
        sys.exit(1)

    input_path = sys.argv[1]
    dtb_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else input_path

    if fix_bootimg(input_path, dtb_path, output_path):
        print("SUCCESS")
    else:
        print("FAILED")
        sys.exit(1)
