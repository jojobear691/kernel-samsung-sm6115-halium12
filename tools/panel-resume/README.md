# SM-T500 panel resume ordering experiment

This is a diagnostic kernel candidate, not a verified hardware repair or a release.
It has not been installed. Both Maliit repairs remain installed and user-confirmed
on the tablet independently of this kernel experiment.

## Observed problem and change

On `4.19.300-perf+ #189`, a captured wake showed a Himax touch reset overlapping
the last part of the panel ON command sequence. The first status check five
seconds later failed, followed by repeated PANEL_DEAD recovery and touch resets.
The device eventually recovered without rebooting. This establishes timing,
not that the touch reset caused the bad panel status.

The DSI driver emits its synthetic UNBLANK notification after panel reset and
before PRE_ON/ON writes. The Himax notifier queues touch resume asynchronously.
The experimental change flushes that resume work before the notifier returns.
Existing suspend and ignored-event behavior is preserved.

## Validation and limits

The test extracts the actual DRM notifier callback into a C/pthread harness.
It holds resume completion at a condition variable and checks what the panel
consumer sees when the callback returns. The original callback fails both
ordering cases; the candidate passes all four cases, including pending work,
ignored notification, and early suspend. This tests callback ordering only.

Read-only review found no demonstrated software lock cycle, but identified two
material risks to check on hardware:

1. The entire worker is now inside the display critical path. `request_firmware`
   can enter userspace fallback (default timeout 60 seconds, configurable), and
   firmware-ready polling can exhaust its retries without returning an error.
   Confirm the firmware is present/readable, measure latency, and compare the
   original build tree before any installation. Completion does not prove
   successful firmware startup before the panel ON commands.
2. The worker enables touch IRQs before it returns. Exception handling can
   upload/reset firmware outside this work item. The barrier therefore cannot
   exclude a subsequent IRQ-driven reset during panel ON. Capture all reset
   and exception events in any controlled device test.

If these risks reproduce, a durable design needs firmware loading outside the
display critical path and separate pre-ON reset and post-ON readiness/IRQ phases.
Returning from a timed wait while resume still runs would recreate the race.

## Build provenance

Public source base: `c058c8a0930d4352eaa96a172f83515077e9ea62` in
`jojobear691/kernel-samsung-sm6115-halium12`, branch `gta4lwifi-halium12`.
The running configuration was read from the tablet; it contains configuration
settings only. The original build folder is on a disconnected hard drive, so
its unpublished changes have not been compared.

The build script pins AOSP Clang r416183b and GNU binutils, checks their reported
versions against the running kernel, rejects configuration drift, records source
commits and hashes, and produces a bare `Image.gz`. It does not package or flash
`boot.img`, replace modules, restart the tablet, or change any installed files.
Matching a compiler version and kernel release does not establish matching ABI;
compare Module.symvers with the original build before reusing external modules.

No raw device traces, boot images, proprietary firmware, credentials, network
identifiers, or user data are included. CI has read-only repository permission,
uses no account secrets, and retains build artifacts for fourteen days.

Rollback for a future approved test: preserve the current boot partition first
and restore that exact image through recovery if needed. No flashing command is
included here; device validation requires a separately reviewed boot candidate.
