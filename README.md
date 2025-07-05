# CEC Flipper Control

Control HDMI-CEC devices using your Flipper Zero and a Raspberry Pi Zero 2 W! This project combines the power of CEC (Consumer Electronics Control) with the versatility of the Flipper Zero for remote device management.

## 🚀 Features

- **Flipper Zero Interface**: Intuitive menu-driven app for controlling CEC devices
- **WiFi Communication**: HTTP interface for device control
- **WiFi Testing**: HTTP interface for easy testing and debugging
- **CEC Commands**: Power on/off, device scanning, status checking, and custom commands
- **Automated Setup**: One-command installation for Raspberry Pi
- **GitHub Actions**: Automatic building and packaging

## 📋 Requirements

### Hardware

- **Raspberry Pi Zero 2 W**
- **Flipper Zero**
- **HDMI-CEC compatible TV/Display**

### Software

- Raspberry Pi OS (tested on Pi OS Lite)
- Flipper Zero firmware (Momentum firmware recommended)

## 🔧 Installation

### Raspberry Pi Setup

**One-command installation:**

```bash
curl -sSL https://raw.githubusercontent.com/dannykeren/cec-flipper-control/main/rpi/install.sh | sudo bash
```

This will:
- Install all necessary dependencies
- Set up CEC communication
- Configure services to start on boot
- Set up HTTP test server

### Flipper Zero Setup

- Download the latest `.fap` file from [Releases](https://github.com/dannykeren/cec-flipper-control/releases)
- Copy to `SD Card/apps/GPIO/cec_remote.fap`
- **Note**: This app requires Momentum firmware

## 🔌 Hardware Setup

1. **Connect HDMI**: Raspberry Pi to your CEC-compatible TV/display
2. **Enable CEC**: Check your TV settings and enable CEC (Samsung: Anynet+, LG: SIMPLINK, Sony: Bravia Sync)
3. **Power On**: Boot up the Raspberry Pi

## 📱 Usage

### Testing via WiFi (Mac/PC)

```bash
# Test connection
curl 'http://[PI_IP]:8080?cmd=PING'

# Test CEC commands  
curl 'http://[PI_IP]:8080?cmd=SCAN'
curl 'http://[PI_IP]:8080?cmd=POWER_ON'
curl 'http://[PI_IP]:8080?cmd=POWER_OFF'
```

### Using the Flipper Zero App

1. **Launch App**: Go to `Apps` → `GPIO` → `CEC Remote`
2. **Connection**: The app will automatically connect to the Raspberry Pi
3. **Control Menu**:
   - **Power ON**: Turn on connected CEC devices
   - **Power OFF**: Turn off connected CEC devices  
   - **Scan Devices**: Discover available CEC devices
   - **Check Status**: Get current device status
   - **Custom Command**: Send raw CEC commands

### Supported CEC Commands

| Command | Description |
|---------|-------------|
| `PING` | Test connection |
| `SCAN` | Scan for CEC devices |
| `POWER_ON` | Turn on all devices |
| `POWER_OFF` | Turn off all devices |
| `STATUS` | Check power status |
| `CUSTOM` | Send custom CEC command |

## 🛠️ Development

### Building from Source

#### Flipper Zero App

```bash
cd flipper
ufbt build
ufbt launch  # Deploy to connected Flipper
```

#### Raspberry Pi Components

```bash
cd rpi
python3 -m py_compile *.py  # Verify syntax
sudo python3 main.py        # Test manually
```

### Project Structure

```
cec-flipper-control/
├── README.md
├── rpi/                          # Raspberry Pi components
│   ├── install.sh               # Automated setup script
│   ├── main.py                  # Main application
│   ├── cec_control.py           # CEC command interface
│   ├── http_test.py             # HTTP test server
│   └── requirements.txt         # Python dependencies
├── flipper/                      # Flipper Zero app
│   ├── application.fam          # App manifest
│   └── cec_remote.c            # Main application code
├── docs/                        # Documentation
└── .github/
    └── workflows/
        └── build.yml           # Automated CI/CD
```

## 🐛 Troubleshooting

### If installer fails:

```bash
ssh pi@[PI_IP]
sudo systemctl status cec-flipper
sudo journalctl -u cec-flipper -f
```

### If CEC commands timeout:

- Verify HDMI connection
- Enable CEC on TV (Samsung: Anynet+, LG: SIMPLINK, etc.)
- Check: `echo "scan" | cec-client -s -d 1`

### CEC commands not working:

- Verify HDMI connection supports CEC
- Test CEC manually: `echo "scan" | cec-client -s -d 1`
- Check TV CEC settings are enabled

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) first.

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Test thoroughly on both RPi and Flipper
5. Commit changes: `git commit -m 'Add amazing feature'`
6. Push to branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **libCEC** - The foundation for CEC communication
- **Flipper Zero Community** - For the amazing platform and tools
- **Momentum Firmware** - For enhanced Flipper Zero capabilities

## 📊 Project Status

![Build Status](https://github.com/dannykeren/cec-flipper-control/workflows/Build%20CEC%20Flipper%20Control/badge.svg)
![Release](https://img.shields.io/github/v/release/dannykeren/cec-flipper-control)
![Downloads](https://img.shields.io/github/downloads/dannykeren/cec-flipper-control/total)

---

**Made with ❤️ for the Flipper Zero and maker communities**
