# Offline Logging for Field Use

## Overview
The CEC tool provides comprehensive offline logging capabilities, perfect for field work where WiFi access is limited or unavailable.

## Features

### Flipper-Based Logging
- All command history accessible via Flipper
- No WiFi required
- Real-time success/failure feedback
- BrightSign export ready for copy-paste

### Log Format
```
[2025-01-15 14:30:15] CMD: POWER_ON
[2025-01-15 14:30:17] POWER_ON: ✅
[2025-01-15 14:30:20] CMD: HDMI_1
[2025-01-15 14:30:22] HDMI_1: ✅
[2025-01-15 14:30:25] CMD: HDMI_2
[2025-01-15 14:30:27] HDMI_2: ❌
```

## Flipper Menu Commands

### View Log
- Shows last 20 command entries
- Displays success/failure status
- Includes timestamps

### Export Log
- Provides BrightSign-ready commands
- JSON format with successful commands only
- Includes hex codes for direct copy-paste

### Clear Log
- Resets all log files
- Useful when moving between different equipment

## Field Workflow

### 1. Test Equipment
```
Connect Flipper + Pi to projector/TV
No WiFi needed
Test commands via Flipper menu
```

### 2. Monitor Results
```
Use "View Log" to see what worked
✅ = Success
❌ = Failure
```

### 3. Export Working Commands
```
Use "Export Log" to get BrightSign format
Copy successful commands to BrightSign project
```

### 4. Document Results
```
Log includes vendor information
Timestamp for documentation
Ready for sharing with team
```

## Example Field Session

### Testing Optoma Projector
```
14:30:15 - CMD: POWER_ON
14:30:17 - POWER_ON: ✅ (Multi-step sequence successful)
14:30:20 - CMD: HDMI_1
14:30:22 - HDMI_1: ✅ (Samsung-style command worked)
14:30:25 - CMD: HDMI_2
14:30:27 - HDMI_2: ❌ (Command failed)
14:30:30 - CMD: VOLUME_UP
14:30:32 - VOLUME_UP: ✅ (Standard command worked)
```

### Export Results
```json
{
  "successful_commands": [
    {
      "command": "POWER_ON",
      "vendor": "optoma",
      "brightsign_command": "BrightControl Send Ascii String \"1004\""
    },
    {
      "command": "HDMI_1",
      "vendor": "optoma", 
      "brightsign_command": "BrightControl Send Ascii String \"4F821000\""
    },
    {
      "command": "VOLUME_UP",
      "vendor": "optoma",
      "brightsign_command": "BrightControl Send Ascii String \"1044\""
    }
  ]
}
```

### Use in BrightSign
```
BrightControl Send Ascii String "1004"      # Power On
BrightControl Send Ascii String "4F821000"  # HDMI 1
BrightControl Send Ascii String "1044"      # Volume Up
```

## Technical Details

### Log File Locations
- **Flipper Log**: `/tmp/flipper_cec_log.txt`
- **BrightSign Export**: `/tmp/flipper_brightsign_export.json`

### Memory Management
- Shows last 20 entries to prevent overflow
- Automatic cleanup options available
- Logs survive Pi reboots

### Success Tracking
- Only successful commands are exported
- Failed commands logged but not exported
- Vendor information included for context

## Use Cases

### 1. Equipment Testing
- Test unknown projectors/TVs
- Document working commands
- Build vendor-specific profiles

### 2. Troubleshooting
- Debug existing BrightSign setups
- Find alternative commands
- Verify CEC compatibility

### 3. Site Deployment
- Arrive with portable tool
- Test customer equipment
- Generate working commands
- Configure BrightSign players
- All offline - no network dependency

### 4. Knowledge Building
- Document successful commands
- Share with team
- Build command library
- Professional documentation

## Advantages

### No Network Required
- Works at any customer site
- No WiFi password needed
- No internet dependency
- Completely self-contained

### Instant Feedback
- See results immediately
- No upload delays
- Real-time success/failure
- Professional confidence

### Portable Documentation
- All logs on Flipper
- Take anywhere
- Copy to laptop when needed
- Share with team

### Professional Workflow
- Systematic testing
- Documented results
- Ready-to-use commands
- Vendor-specific notes

## Best Practices

### 1. Test Systematically
Always test in this order:
1. Power commands (ON/OFF/STATUS)
2. Input switching (HDMI 1-4)
3. Volume control (UP/DOWN/MUTE)
4. Custom commands if needed

### 2. Clear Logs Between Sites
Use "Clear Log" when testing different equipment to avoid confusion.

### 3. Document Findings
Export logs include vendor and timing information for future reference.

### 4. Build Command Library
Keep successful exports for different equipment models.

### 5. Share Knowledge
Export format is perfect for sharing working commands with colleagues.
