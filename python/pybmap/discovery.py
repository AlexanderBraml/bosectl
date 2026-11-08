"""Auto-detect paired BMAP devices (Linux/macOS)."""

import re

# Only a literal MAC is handed on to bluetoothctl, mirroring the C++ guard.
_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")

import sys

if sys.platform == "darwin":
    from IOBluetooth import IOBluetoothDevice
    from .catalog import lookup_device

    def find_bmap_device(connected_only=False):
        """Auto-detect a paired, connected BMAP-capable Bluetooth device on macOS.

        Prioritizes connected devices over paired-but-disconnected ones.
        With connected_only, a paired-but-disconnected device is never
        returned, so callers fail fast instead of paging an absent headset.
        Returns (mac, device_type) tuple, or (None, None) if not found.
        """
        candidates = []
        try:
            for device in IOBluetoothDevice.pairedDevices():
                pid = device.productID()
                entry = lookup_device(pid)
                if entry and entry.config:
                    # device.getAddressString() returns something like "68-f2-1f-0d-f5-11"
                    candidates.append((device.getAddressString(), entry.config, device.isConnected()))
        except Exception:
            pass

        # Prefer connected devices
        for mac, device_type, connected in candidates:
            if connected:
                return (mac, device_type)

        if connected_only:
            return (None, None)

        # Fall back to first paired BMAP device
        for mac, device_type, connected in candidates:
            return (mac, device_type)

        return (None, None)

else:
    import re
    import subprocess
    from .catalog import BMAP_UUID, BOSE_USB_VID, lookup_device

    def find_bmap_device(connected_only=False):
        """Auto-detect a paired, connected BMAP-capable Bluetooth device (Linux).

        Prioritizes connected devices over paired-but-disconnected ones.
        With connected_only, only connected devices are scanned and a
        paired-but-disconnected device is never returned, so callers fail
        fast instead of paging an absent headset.
        Returns (mac, device_type) tuple, or (None, None) if not found.
        """
        candidates = _scan_paired_devices(connected_only)

        # Prefer connected devices
        for mac, device_type, connected in candidates:
            if connected:
                return (mac, device_type)

        if connected_only:
            return (None, None)

        # Fall back to first paired BMAP device
        for mac, device_type, connected in candidates:
            return (mac, device_type)

        return (None, None)


    def _scan_paired_devices(connected_only=False):
        """Scan paired Bluetooth devices for BMAP-capable headphones.

        With connected_only, list only connected devices, which saves one
        `bluetoothctl info` call per paired-but-disconnected device. Older
        bluetoothctl versions ignore the filter; the "Connected: yes" check
        below still applies.
        """
        candidates = []
        try:
            result = subprocess.run(
                ["bluetoothctl", "devices", "Connected" if connected_only else "Paired"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.strip().splitlines():
                parts = line.split(None, 2)
                if len(parts) < 2:
                    continue
                mac = parts[1]
                if not _MAC_RE.match(mac):
                    continue
                info = subprocess.run(
                    ["bluetoothctl", "info", mac],
                    capture_output=True, text=True, timeout=3,
                )
                info_text = info.stdout

                # Must be an audio device with the BMAP UUID
                is_audio = ("audio-headset" in info_text or "audio-headphones" in info_text)
                has_bmap = BMAP_UUID in info_text
                if not (is_audio and has_bmap):
                    continue
                # The BMAP UUID is not unique to Bose (e.g. Sony LinkBuds S
                # advertise it too); skip devices of another vendor.
                if not _is_bose_vendor(info_text):
                    continue

                connected = "Connected: yes" in info_text

                # Determine device type from Modalias product ID
                device_type = _detect_device_type(info_text)

                candidates.append((mac, device_type, connected))
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return candidates


    # Bose's Bluetooth SIG company ID and USB vendor ID, as seen in Modalias.
    _BOSE_VENDORS = {("bluetooth", 0x009E), ("bluetooth", BOSE_USB_VID), ("usb", BOSE_USB_VID)}

    def _is_bose_vendor(info_text):
        """False if the device's Modalias names a vendor other than Bose.

        Devices without a Modalias are accepted, as before.
        """
        match = re.search(r"Modalias:\s*(bluetooth|usb):v([0-9A-Fa-f]{4})", info_text)
        if not match:
            return True
        return (match.group(1), int(match.group(2), 16)) in _BOSE_VENDORS


    def _detect_device_type(info_text):
        """Extract device type from bluetoothctl info output via catalog lookup."""
        match = re.search(r"Modalias:\s*bluetooth:v[0-9A-Fa-f]{4}p([0-9A-Fa-f]{4})", info_text)
        if match:
            product_id = int(match.group(1), 16)
            entry = lookup_device(product_id)
            if entry and entry.config:
                return entry.config
        return "qc_ultra2"  # default for unknown BMAP devices
