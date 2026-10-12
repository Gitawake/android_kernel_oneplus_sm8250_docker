# OnePlus 8 Pro: LOS 23.2 + Debian chroot Docker + KernelSU Next

Reproducible GitHub Actions build recipe for **instantnoodlep / IN2020**, matching **LineageOS 23.2-20260313-NIGHTLY**.

- LOS source: https://github.com/LineageOS/android_kernel_oneplus_sm8250 at `0970a5d23405622c10bc4ff60ef0ba30499611e1` (4.19.325-cip128-st12).
- Official KernelSU Next v3.4.1: `8f902aeb16033024143ae36cf711df902cf02fae`.
- Build on GitHub Ubuntu 24.04 runners with Clang/LLVM 18.
- Use the running device's original kernel configuration; merge Docker and KSU requirements and assert that every requested feature survives Kconfig.
- Preserve original LOS ramdisk, DTB and boot header when packaging. No Magisk ramdisk is included in the KSU candidate. No SELinux disablement.

The repository contains a build recipe and patches. CI downloads the exact upstream kernel and official KSU release. The KSU port is based on the previous hotdog LOS 4.14 port, adapted for this exact LOS 4.19 tree, including task_work, fsnotify, file operations, seccomp and transactional SELinux policy handling.

## Build

Open Actions → OnePlus 8 Pro LOS Docker + KernelSU Next → Run workflow. Pushing to main also triggers a build. A passing full build and boot repack are necessary, but do not establish device stability or successful Docker operation.

## Runtime target

Android stays as the host. Debian runs in a real root chroot. This device currently uses a hybrid cgroup layout: Android binds CPU/blkio/cpuset to v1 and memory to v2. Preserve those mounts. Docker needs a coherent view inside its mount namespace; verify available controllers and use a dedicated subtree. Do not rebind Android's memory controller or assume a generic desktop cgroup setup. A v2 view can expose memory and the newly enabled pids controller; CPU/IO limits require additional runtime planning because Android already owns the v1 hierarchies. Run dockerd directly with the cgroupfs driver: chroot does not start systemd as PID 1.

Prefer a separate ext4 image for the Debian root/data on Android's F2FS /data. Bind /dev, mount proc/sysfs/devpts, verify mount propagation and overlay2, then test container creation, bridge networking, DNS, outbound traffic, published ports and Compose. Existing Android tethering and sing-box firewall rules must be preserved. Passing the kernel configuration check alone is not end-to-end Docker validation.

## Validation and rollback

Current Magisk boot and original LOS boot are backed up locally. The build candidate uses original LOS ramdisk with built-in KSU-N. Before any permanent flash, verify bootloader unlock/current slot, temporarily boot the candidate and test Android, Wi-Fi, root, SELinux Enforcing, logs and Docker. Do not assume a slot from another device or build. No phone partitions are modified by this build workflow.

The supplied original boot input was recovered from Magisk's backup and its SHA-1 matched the backup identifier `cde15611b1ba8a2948539501559f2185c2ef6a5c`. CI verifies its compressed SHA-256 and checks ramdisk/DTB preservation when repacking.

## Device-test finding and fix

The first candidate booted Android with SELinux Enforcing and the manager signature was recognized, but the manager's exec-ed ksud lost the CLOEXEC driver fd and Android app seccomp blocked the reboot-based reinstallation handshake. The 4.19 port now exempts only the exact native ARM64 KSU fd-install magic request for the verified manager or an already-authorized root UID. Other calls still evaluate every seccomp filter; the driver's root ioctl authorization remains unchanged. This replaces the newer action-cache allow mechanism absent from 4.19.

The seccomp-fixed candidate passed Android, Wi-Fi, KernelSU root, Enforcing and namespace/chroot tests. A baseline comparison found a new jump-label warning pointing to built-in KSU exit text. The port omits the module-unload callback when CONFIG_KSU=y, while preserving it for MODULE builds, so discarded exit text cannot leave a static-key jump entry.
