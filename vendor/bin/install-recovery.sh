#!/vendor/bin/sh
# added for checking whether if last normal-boot (after ota) finished or not      01/15/2019@chenyuqin
/vendor/bin/dd if=/dev/zero of=/dev/block/bootdevice/by-name/reserved bs=1 count=8 seek=3672072 conv=notrunc && log -t recovery "succeeded to clear last-normal-boot-retry-count" || log -t recovery "failed to clear last-normal-boot-retry-count"
/vendor/bin/dd if=/dev/zero of=/dev/block/bootdevice/by-name/reserved bs=1 count=8 seek=3672088 conv=notrunc && log -t recovery "succeeded to clear last-ota-to-boot-retry-count" || log -t recovery "failed to clear last-ota-to-boot-retry-count"
if ! applypatch --check EMMC:/dev/block/by-name/recovery$(getprop ro.boot.slot_suffix):100663296:1e2c5c59c267ae7b47df30ea4b0fd59826504b4c; then
  applypatch  \
          --patch /vendor/recovery-from-boot.p \
          --source EMMC:/dev/block/by-name/boot$(getprop ro.boot.slot_suffix):100663296:801d158fd8a65b1bcdd34e527da95942444ff1a5 \
          --target EMMC:/dev/block/by-name/recovery$(getprop ro.boot.slot_suffix):100663296:1e2c5c59c267ae7b47df30ea4b0fd59826504b4c && \
      log -t recovery "Installing new recovery image: succeeded" || \
      log -t recovery "Installing new recovery image: failed"
else
  log -t recovery "Recovery image already installed"
fi
