#!/bin/bash

echo "========================================="
echo "  CEC Flipper Control - Minimal Setup"
echo "   Fresh Raspberry Pi Zero W"
echo "========================================="

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run with sudo: sudo bash $0"
  exit 1
fi

echo "🔄 Updating system..."
apt update && apt upgrade -y

echo "📦 Installing required packages..."
apt install -y cec-utils python3-pip python3-venv git

echo "🔧 Configuring USB gadget mode..."

INSTALL_DIR="/opt/cec-flipper"
mkdir -p $INSTALL_DIR

python3 -m venv $INSTALL_DIR/venv
source $INSTALL_DIR/venv/bin/activate
pip install pyserial

echo "📥 Downloading application files..."

# Download files with proper error handling
if curl -sSL "https://raw.githubusercontent.com/dannykeren/cec-flipper-control/main/rpi/cec_control.py" > $INSTALL_DIR/cec_control.py; then
    echo "✅ Downloaded cec_control.py"
else
    echo "❌ Failed to download cec_control.py"
    exit 1
fi

if curl -sSL "https://raw.githubusercontent.com/dannykeren/cec-flipper-control/main/rpi/main.py" > $INSTALL_DIR/main.py; then
    echo "✅ Downloaded main.py"
else
    echo "❌ Failed to download main.py"
    exit 1
fi

chmod +x $INSTALL_DIR/main.py

# Download HTTP test server
if curl -sSL "https://raw.githubusercontent.com/dannykeren/cec-flipper-control/main/rpi/http_test.py" > $INSTALL_DIR/http_test.py; then
    echo "✅ Downloaded http_test.py"
else
    echo "❌ Failed to download http_test.py"
    exit 1
fi

chmod +x $INSTALL_DIR/http_test.py

cat > /etc/systemd/system/cec-flipper.service << EOFINNER
[Unit]
Description=CEC Flipper Control
After=usb-gadget.service
Requires=usb-gadget.service

[Service]
Type=simple
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py
WorkingDirectory=$INSTALL_DIR
Restart=always
RestartSec=5
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOFINNER

systemctl enable usb-gadget.service
systemctl enable cec-flipper.service

CURRENT_USER=$(logname 2>/dev/null || echo "pi")
usermod -a -G dialout,tty $CURRENT_USER

echo "Setup complete! Reboot required."
read -p "Reboot now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  reboot
fi
