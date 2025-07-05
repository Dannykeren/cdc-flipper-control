# BrightSign Export Guide

## Overview
The CEC tool automatically captures successful commands and exports them in BrightSign-compatible format, eliminating the need for manual hex code conversion.

## How It Works

### Automatic Command Tracking
- Every CEC command is logged with timestamp and result
- Successful commands are tracked separately
- Vendor information is included for context
- Raw hex codes are preserved for export

### BrightSign Format Conversion
- Raw CEC commands are converted to BrightSign ASCII format
- Proper BrightControl command syntax is generated
- Ready for copy-paste into BrightSign presentations

## Export Format

### JSON Structure
```json
{
  "export_time": "2025-01-15T10:30:00",
  "total_successful_commands": 3,
  "commands": [
    {
      "timestamp": "2025-01-15T10:25:00",
      "command": "POWER_ON",
      "vendor": "optoma",
      "raw_cec_command": "tx 10:04"
    }
  ],
  "brightsign_format": [
    {
      "description": "Vendor: optoma | Original: tx 10:04",
      "brightsign_ascii": "1004",
      "brightsign_command": "BrightControl Send Ascii String \"1004\"",
      "timestamp": "2025-01-15T10:25:00"
    }
  ]
}
```

### BrightSign Commands
The `brightsign_command` field contains the exact command to use in BrightSign:
```
BrightControl Send Ascii String "1004"
BrightControl Send Ascii String "4F821000"
BrightControl Send Ascii String "1044"
```

## Access Methods

### Via Flipper Zero
1. Use any CEC command (Power ON, HDMI switching, etc.)
2. Select "Export Log" from Flipper menu
3. View BrightSign-ready commands on screen
4. Copy commands to BrightSign project

### Via HTTP (when available)
```bash
# Get BrightSign export
curl 'http://[PI_IP]:8080?cmd=GET_BRIGHTSIGN_EXPORT'

# Get Flipper-accessible export
curl 'http://[PI_IP]:8080?cmd=GET_FLIPPER_EXPORT'
```

## Workflow Examples

### Example 1: Optoma Projector
**Test Commands:**
```
Power ON → ✅ Success
HDMI 1 → ✅ Success
HDMI 2 → ❌ Failed
Volume Up → ✅ Success
```

**Export Result:**
```json
{
  "brightsign_format": [
    {
      "description": "Vendor: optoma | Original: tx 10:04",
      "brightsign_ascii": "1004",
      "brightsign_command": "BrightControl Send Ascii String \"1004\""
    },
    {
      "description": "Vendor: optoma | Original: tx 10:82:10:00",
      "brightsign_ascii": "10821000",
      "brightsign_command": "BrightControl Send Ascii String \"10821000\""
    },
    {
      "description": "Vendor: optoma | Original: volup",
      "brightsign_ascii": "1044",
      "brightsign_command": "BrightControl Send Ascii String \"1044\""
    }
  ]
}
```

**Use in BrightSign:**
```
BrightControl Send Ascii String "1004"      # Power On
BrightControl Send Ascii String "10821000"  # HDMI 1
BrightControl Send Ascii String "1044"      # Volume Up
```

### Example 2: Samsung TV
**Test Commands:**
```
Power ON → ✅ Success
HDMI 1 → ✅ Success
HDMI 2 → ✅ Success
TV Input → ✅ Success
```

**Export Result:**
```json
{
  "brightsign_format": [
    {
      "description": "Vendor: samsung | Original: tx 4F:82:10:00",
      "brightsign_ascii": "4F821000",
      "brightsign_command": "BrightControl Send Ascii String \"4F821000\""
    },
    {
      "description": "Vendor: samsung | Original: tx 4F:82:20:00",
      "brightsign_ascii": "4F822000",
      "brightsign_command": "BrightControl Send Ascii String \"4F822000\""
    },
    {
      "description": "Vendor: samsung | Original: tx 4F:9D:00:00",
      "brightsign_ascii": "4F9D0000",
      "brightsign_command": "BrightControl Send Ascii String \"4F9D0000\""
    }
  ]
}
```

## Command Conversion Table

### Common CEC Commands
| CEC Command | BrightSign ASCII | Description |
|-------------|------------------|-------------|
| `tx 10:04` | `1004` | Image View On (Power) |
| `tx 10:36` | `1036` | Standby (Power Off) |
| `tx 4F:82:10:00` | `4F821000` | HDMI 1 (Samsung) |
| `tx 4F:82:20:00` | `4F822000` | HDMI 2 (Samsung) |
| `tx 10:44:41` | `104441` | Volume Up |
| `tx 10:44:42` | `104442` | Volume Down |
| `tx 10:44:43` | `104443` | Mute |

### Vendor-Specific Commands
| Vendor | Command | BrightSign ASCII | Description |
|--------|---------|------------------|-------------|
| Optoma | `tx 10:04` | `1004` | Power On (Step 1) |
| Optoma | `tx 10:82:10:00` | `10821000` | Active Source |
| Optoma | `tx 10:04` | `1004` | Power On (Step 2) |
| NEC | `tx 10:04` | `1004` | Power On (CEC v1.4) |
| Epson | `tx 10:8C` | `108C` | CEC Wake-up |
| Samsung | `tx 4F:82:10:00` | `4F821000` | Anynet+ HDMI 1 |
| LG | `tx 10:44:F1` | `1044F1` | SimpLink HDMI 1 |

## BrightSign Implementation

### In BrightAuthor
1. Add Interactive → CEC Control
2. Use "BrightControl Send Ascii String" command
3. Copy hex codes from export
4. Test with your equipment

### Example BrightSign Script
```
' Power on projector
BrightControl Send Ascii String "1004"
Wait 2000

' Switch to HDMI 1
BrightControl Send Ascii String "4F821000"
Wait 1000

' Set volume
BrightControl Send Ascii String "1044"
```

### Timing Considerations
- Add appropriate delays between commands
- Optoma: 1 second delays
- NEC: 2 second delays  
- Epson: 1.5 second delays
- Test timing with your specific equipment

## Troubleshooting

### Common Issues
1. **Commands not working**: Verify hex codes are correct
2. **Timing issues**: Add longer delays between commands
3. **Vendor-specific problems**: Check if multi-step sequences are needed

### Debug Process
1. Test commands via Flipper first
2. Verify commands work before using in BrightSign
3. Check export format for correct hex codes
4. Test timing delays

### Export Problems
- If export is empty: No successful commands recorded
- If hex codes look wrong: Check original CEC commands
- If vendor is generic: Vendor detection may have failed

## Best Practices

### 1. Test Before Export
Always test commands via Flipper to ensure they work before exporting.

### 2. Verify Hex Codes
Compare exported hex codes with original CEC commands to ensure accuracy.

### 3. Document Timing
Note required delays between commands for each vendor.

### 4. Test in BrightSign
Always test exported commands in BrightSign before deployment.

### 5. Keep Records
Save successful exports for different equipment models.

### 6. Share Knowledge
Export format is perfect for sharing working commands with team members.
