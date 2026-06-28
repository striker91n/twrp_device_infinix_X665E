import struct
import os
import sys

def page_align(size, page_size):
    return ((size + page_size - 1) // page_size) * page_size

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

    # Calculate component offsets
    kernel_offset = header_size
    kernel_padded = page_align(kernel_size, page_size)
    ramdisk_offset = kernel_offset + kernel_padded
    ramdisk_padded = page_align(ramdisk_size, page_size)

    # DTB starts after ramdisk
    dtb_data_start = ramdisk_offset + ramdisk_padded
    dtb_size = len(data) - dtb_data_start

    if dtb_size <= 0:
        print("ERROR: No DTB area found")
        return False

    print(f"Existing DTB area: offset={dtb_data_start}, size={dtb_size}")
    print(f"First bytes: {data[dtb_data_start:dtb_data_start+4].hex()}")

    # Read the prebuilt MKDTIMG
    with open(dtb_path, 'rb') as f:
        mkdtimg = f.read()
    print(f"MKDTIMG DTB size: {len(mkdtimg)}")

    # Reconstruct: header + kernel + ramdisk + MKDTIMG DTB + padding to target_size
    new_dtb_padded = page_align(len(mkdtimg), page_size)
    new_size = dtb_data_start + new_dtb_padded

    if new_size > target_size:
        print(f"ERROR: Image too large ({new_size} > {target_size})")
        return False

    result = bytearray(target_size)
    result[:dtb_data_start] = data[:dtb_data_start]
    result[dtb_data_start:dtb_data_start + len(mkdtimg)] = mkdtimg

    # Zero out DTB header v2 fields (let bootloader scan for it)
    if header_version >= 2 and len(data) >= 1632:
        struct.pack_into('<I', result, 1640, 0)
        struct.pack_into('<I', result, 1644, 0)

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
