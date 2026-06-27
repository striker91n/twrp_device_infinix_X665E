$(call inherit-product, vendor/omni/config/common.mk)

PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/recovery.fstab:recovery/root/system/etc/recovery.fstab

PRODUCT_PACKAGES += \

PRODUCT_NAME := omni_X665E
PRODUCT_DEVICE := X665E
PRODUCT_BRAND := Infinix
PRODUCT_MODEL := Infinix X665E
PRODUCT_MANUFACTURER := INFINIX
PRODUCT_RELEASE_NAME := X665E-GL
