# M4.9 Change Log

## M4.9.2

- Restored the complete `BeaconRuntime` composition root after the M4.9.1
  packaging regression.
- Retained the classifier's raw pre-verification state for hysteresis feedback.
- Added an integration regression test covering VERIFIED_BEACON followed by an
  SNR value inside the PROBABLE_BEACON hysteresis band.
- Removed the unused standalone helper with the invalid `analyze()` call.
- Excluded stale and non-portable review artifacts from the update package.
