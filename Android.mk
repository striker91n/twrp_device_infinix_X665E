LOCAL_PATH := $(call my-dir)

ifneq ($(filter X665E,$(TARGET_DEVICE)),)

include $(call all-makefiles-under,$(LOCAL_PATH))

endif
