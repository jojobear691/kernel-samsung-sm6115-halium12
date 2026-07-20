# Samsung Galaxy Tab A7 Wi-Fi Ubuntu Touch kernel

Experimental Linux 4.19.300 kernel source for the Samsung Galaxy Tab A7
Wi-Fi, model SM-T500, codename `gta4lwifi`, used by the Ubuntu Touch
24.04 / Halium 12 community port.

> [!WARNING]
> This branch is intended only for the Wi-Fi SM-T500 (`gta4lwifi`).
> Do not flash its output on SM-T505, SM-T505C, SM-T505N, SM-T507, or
> other LTE `gta4l` variants. Bluetooth support remains experimental and
> may cause connection failures, loss of pairing state, or hard reboots.

## Branch and source snapshot

Use the `gta4lwifi-halium12` branch.

The first public experimental Bluetooth source snapshot is:

`4f1afef068c5c095e51c2f8870f0e3cd50c3d363`

Later commits may harden or document that snapshot without implying that
Bluetooth is production-ready.

This repository contains the kernel half of the port. A kernel build by
itself is not a complete Ubuntu Touch installation.

## Port integration

The matching Ubuntu Touch port repository is:

<https://github.com/jojobear691/ubuntu-touch-samsung-gta4lwifi>

Its device configuration declares:

- kernel branch: `gta4lwifi-halium12`;
- defconfig inputs: `gta4l_eur_open_defconfig halium.config`;
- kernel image: `Image.gz`;
- build targets: `Image.gz modules`;
- architecture: AArch64;
- compiler route: Clang through the UBports adaptation build tools.

The `gta4l` defconfig name comes from Samsung's kernel configuration. It
does not make this branch safe for LTE tablet variants.

## Build route

The currently documented build entry point is the matching port
repository:

    git clone https://github.com/jojobear691/ubuntu-touch-samsung-gta4lwifi.git
    cd ubuntu-touch-samsung-gta4lwifi
    ./build.sh

The inspected UBports adaptation build-tools revision was:

`c48c8a8c65f19a025fbfa217b5fe8695c443ce59`

The port build script currently follows the build-tools `main` branch,
and the exact Clang toolchain identity is not pinned here. This README
therefore does not claim bit-for-bit reproducible kernel builds.

## Experimental Bluetooth path

The intended runtime path is:

1. the Qualcomm Android Bluetooth HAL;
2. Bluebinder in Ubuntu Touch userspace;
3. the kernel `/dev/vhci` interface;
4. a Linux virtual HCI controller;
5. BlueZ and Ubuntu Touch applications.

The public snapshot includes VHCI, management, L2CAP, HID, configuration,
diagnostic, and safety-fence work. It records bring-up progress, not a
general Bluetooth stability guarantee.

Publication hardening removes a device-specific controller address from
unreachable diagnostic code and prevents Bluetooth link-key bytes from
being written to kernel logs.

Detailed status and source identities are intended for:

- `docs/BLUETOOTH.md`;
- `provenance/gta4lwifi-bluetooth-source-manifest.txt`;
- `checksums/BLUETOOTH_SOURCE_SHA256SUMS`.

## Publication boundary

This repository should contain reviewable kernel source and
documentation. It should not contain:

- compiled kernel images or modules;
- proprietary Samsung or Qualcomm firmware;
- private runtime logs or crash archives;
- Bluetooth link keys, credentials, tokens, or device-user data.

The existing kernel licensing information remains in `COPYING`.
Imported components retain their respective upstream licenses.
