import re
with open('bootable/recovery/Android.mk', 'r') as f:
    content = f.read()
old = '''ifneq ($(TW_EXCLUDE_ENCRYPTED_BACKUPS),)
    LOCAL_SHARED_LIBRARIES += libopenaes
else
    LOCAL_CFLAGS += -DTW_EXCLUDE_ENCRYPTED_BACKUPS'''
new = '''ifneq ($(TW_EXCLUDE_ENCRYPTED_BACKUPS),)
    LOCAL_CFLAGS += -DTW_EXCLUDE_ENCRYPTED_BACKUPS
else
    LOCAL_SHARED_LIBRARIES += libopenaes'''
if old in content:
    content = content.replace(old, new, 1)
    with open('bootable/recovery/Android.mk', 'w') as f:
        f.write(content)
    print('Patched openaes logic in Android.mk')
else:
    print('Pattern not found, checking current content...')
    for i, line in enumerate(content.split('\n')):
        if 'TW_EXCLUDE_ENCRYPTED' in line:
            print(f'  Line {i+1}: {line}')
