# Experimental Bluetooth support

## Scope and status

This document describes the experimental Bluetooth kernel work for the
Samsung Galaxy Tab A7 Wi-Fi, model SM-T500, codename `gta4lwifi`, as
reviewed on 2026-07-19.

The first public source snapshot is:

`4f1afef068c5c095e51c2f8870f0e3cd50c3d363`

The snapshot is bring-up and diagnostic work. It is not a declaration
that Bluetooth is production-ready. Connections may fail, pairing state
may be lost, and some operations may hard-reboot the tablet.

This branch is not intended for LTE `gta4l` variants.

## Runtime architecture

The intended Ubuntu Touch runtime path is:

1. Qualcomm's Android Bluetooth HAL communicates with the controller;
2. Bluebinder connects the Android HAL to Ubuntu Touch userspace;
3. Bluebinder uses the kernel `/dev/vhci` interface;
4. the kernel exposes a virtual HCI controller such as `hci0`;
5. BlueZ provides Bluetooth services to Ubuntu Touch applications.

The Android side uses the QTI Bluetooth service:

`/vendor/bin/hw/android.hardware.bluetooth@1.0-service-qti`

The platform Bluetooth system-on-chip identifier observed during porting
was `cherokee`.

The kernel repository contains only the kernel portion of this path.
A complete working system also requires the matching Android vendor
components, Ubuntu Touch userspace packages, service configuration, and
device integration. Those userspace changes have not yet been published
as one complete, reproducible Bluetooth deployment record.

## Kernel configuration

The reviewed configuration includes these relevant settings:

- `CONFIG_BT=y`;
- `CONFIG_BT_HCIVHCI=y`;
- `CONFIG_BT_RFCOMM=y`;
- `CONFIG_BT_BNEP=y`;
- `CONFIG_BT_HIDP=y`;
- `CONFIG_BT_HCIUART=y`;
- `CONFIG_BT_HCIUART_QCA=y`.

The port build combines:

`gta4l_eur_open_defconfig halium.config`

The configured build targets are `Image.gz modules`.

## Source areas in the public snapshot

The experimental snapshot changes 14 tracked source or configuration
files covering:

- kernel Bluetooth configuration;
- the VHCI transport;
- Bluetooth management command handling;
- HCI core, request, event, and socket handling;
- L2CAP signaling;
- HID and DualShock handling;
- Bluetooth object selection and diagnostic helpers.

The exact file identities are recorded separately in
`provenance/gta4lwifi-bluetooth-source-manifest.txt`.

## Virtual-controller behavior

Many experimental paths are gated on `HCI_VIRTUAL`. That condition
describes the controller transport, not this tablet alone. If another
virtual HCI controller is used with this kernel, those paths may affect
it as well.

Diagnostic markers with names beginning `GTA4LWIFI_` record the sequence
of bring-up experiments. Their presence does not prove that the marked
operation is safe or required for every controller.

The snapshot contains targeted skips, synthetic completions, event
filtering, and safety fences. These may change normal Linux Bluetooth
semantics and require careful device testing before wider use.

A marker describing a full signaling release records an experimental
milestone only. It is not a general L2CAP, HID, audio, or controller
stability guarantee.

## Publication hardening

The follow-up publication hardening makes two source changes:

1. It removes unreachable success-only connection diagnostic blocks
   that were nested inside a failure-only branch. One block also
   contained a device-specific controller address.
2. It stops a virtual-controller diagnostic from printing Bluetooth
   link-key bytes. The remaining message reports non-secret metadata
   and explicitly says `key_material_redacted`.

The hardening does not remove droidmedia, alter the camera publication,
change the tablet, or modify the separate LineageOS source tree.

Other experimental diagnostics may still report peer addresses,
connection handles, controller names, object addresses, or kernel
pointer values. Runtime logs must therefore still be reviewed and
sanitized before public sharing.

## Known limitations

The current source should be treated as experimental because:

- several code paths intentionally diverge from normal upstream
  Bluetooth behavior;
- some workarounds apply broadly to virtual HCI controllers;
- the complete matching userspace change set is not yet published;
- the exact compiler toolchain identity is not pinned;
- repeatable validation across controllers and Bluetooth profiles has
  not been established;
- hard-reboot behavior observed during controller testing has not been
  fully root-caused.

No claim is made here that pairing persistence, HID, audio, networking,
suspend/resume, or long-running reconnection behavior is reliable.

## Safe reporting

Before publishing a Bluetooth log, remove or review:

- link keys and long-term keys;
- controller and peer addresses;
- device names tied to people;
- authentication material;
- kernel pointers and memory contents;
- usernames, home-directory paths, and private filesystem locations.

Private proof archives and raw diagnostic logs do not belong in this
repository.

## Next work

Future work should be handled separately from this hardening publication:

- identify the minimal kernel workaround set;
- replace broad `HCI_VIRTUAL` behavior with tighter device scoping;
- publish and document the matching userspace configuration;
- test pairing persistence and reconnection;
- test supported profiles individually;
- reduce diagnostic logging;
- document the exact compiler and build environment;
- upstream generally useful fixes where appropriate.
