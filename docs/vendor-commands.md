# CEC Vendor-Specific Commands Guide

## Overview
This document describes vendor-specific CEC command implementations for different projector and TV manufacturers.

## Supported Vendors

### Optoma Projectors
- **Issue**: Standard power-on commands often fail
- **Solution**: Multi-step power-on sequence with retries
- **Commands**:
  ```
  tx 10:04        # Image View On
  tx 10:82:10:00  # Active Source HDMI1
  tx 10:04        # Image View On (retry)
  ```
- **Timing**: 1 second delays, 3 retry attempts

### NEC Projectors
- **Issue**: Requires specific CEC version and longer delays
- **Solution**: CEC v1.4 compatibility with extended timing
- **Commands**:
  ```
  tx 10:04        # Image View On
  tx 10:82:10:00  # Active Source HDMI1
  ```
- **Timing**: 2 second delays, CEC version 1.4 required

### Epson Projectors
- **Issue**: CEC needs reset after power cycle
- **Solution**: CEC wake-up sequence with reset
- **Commands**:
  ```
  tx 10:8C        # CEC wake-up (Get Vendor ID)
  tx 10:04        # Image View On
  tx 10:82:10:00  # Active Source HDMI1
  tx 10:8C        # CEC confirm
  ```
- **Timing**: 1.5 second delays, automatic CEC reset

### Samsung TVs
- **Feature**: Anynet+ input switching
- **Commands**:
  ```
  tx 4F:82:10:00  # HDMI 1
  tx 4F:82:20:00  # HDMI 2
  tx 4F:82:30:00  # HDMI 3
  tx 4F:82:40:00  # HDMI 4
  tx 4F:9D:00:00  # TV Input
  ```

### LG TVs
- **Feature**: SimpLink commands
- **Commands**:
  ```
  tx 10:44:F1     # HDMI 1
  tx 10:44:F2     # HDMI 2
  tx 10:44:F3     # HDMI 3
  tx 10:44:F4     # HDMI 4
  ```

## Implementation Details

### Automatic Vendor Detection
The system automatically detects vendor from CEC scan results:
- Scans for device vendor information
- Applies appropriate command sequences
- Falls back to generic commands if vendor unknown

### Command Logging
All vendor-specific commands are logged with:
- Timestamp
- Command sequence
- Success/failure status
- Vendor information

### BrightSign Export
Successful vendor-specific commands are automatically converted to BrightSign format:
```
BrightControl Send Ascii String "1004"      # Optoma Power On
BrightControl Send Ascii String "4F821000"  # Samsung HDMI 1
```

## Usage Examples

### Testing Optoma Projector
```bash
# Via HTTP
curl 'http://[PI_IP]:8080?cmd=POWER_ON'

# Via Flipper
Use "Power ON" menu item
```

### Testing NEC Projector
```bash
# System automatically applies CEC v1.4 and extended delays
curl 'http://[PI_IP]:8080?cmd=POWER_ON'
```

### Testing Epson Projector
```bash
# System automatically performs CEC reset sequence
curl 'http://[PI_IP]:8080?cmd=POWER_ON'
```

## Troubleshooting

### Common Issues
1. **Power-on fails**: Check vendor-specific sequences are being applied
2. **Input switching fails**: Verify vendor-specific input commands
3. **Commands timeout**: Increase delays for problematic vendors

### Debug Commands
```bash
# Check detected vendor
curl 'http://[PI_IP]:8080?cmd=SCAN'

# View command log
curl 'http://[PI_IP]:8080?cmd=GET_COMMAND_LOG'

# Get BrightSign export
curl 'http://[PI_IP]:8080?cmd=GET_BRIGHTSIGN_EXPORT'
```

## Adding New Vendors

To add support for a new vendor:

1. Add vendor configuration to `VENDOR_CONFIGS` in `cec_control.py`
2. Add vendor detection logic in `get_device_vendor()`
3. Test and document command sequences
4. Add to this documentation

Example vendor configuration:
```python
"new_vendor": {
    "power_on_sequence": [
        "tx 10:04",        # Image View On
        "tx 10:82:10:00",  # Active Source HDMI1
    ],
    "power_on_delay": 1.0,
    "retry_count": 2,
    "input_commands": {
        "hdmi1": "tx 4F:82:10:00",
        "hdmi2": "tx 4F:82:20:00",
    }
}
```
