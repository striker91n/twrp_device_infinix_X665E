$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/base.mk)

PRODUCT_PACKAGES += \
    recovery

PRODUCT_NAME := twrp_X665E
PRODUCT_DEVICE := X665E
PRODUCT_BRAND := Infinix
PRODUCT_MODEL := Infinix X665E
PRODUCT_MANUFACTURER := INFINIX
PRODUCT_RELEASE_NAME := X665E-GL
