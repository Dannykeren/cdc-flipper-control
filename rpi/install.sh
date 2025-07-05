#!/bin/bash

echo "========================================="
echo "  CEC Flipper Control - Setup with UART"
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

echo "🔧 Enabling UART for Flipper communication..."
# Enable UART and disable Bluetooth (check if already exists first)
if ! grep -q "enable_uart=1" /boot/config.txt; then
    echo "enable_uart=1" >> /boot/config.txt
fi
if ! grep -q "dtoverlay=disable-bt" /boot/config.txt; then
    echo "dtoverlay=disable-bt" >> /boot/config.txt
fi
# Also add miniuart overlay to ensure proper UART
if ! grep -q "dtoverlay=miniuart-bt" /boot/config.txt; then
    echo "dtoverlay=miniuart-bt" >> /boot/config.txt
fi
# Remove console from UART
sed -i 's/console=serial0,115200 //' /boot/cmdline.txt
sed -i 's/console=ttyAMA0,115200 //' /boot/cmdline.txt

echo "🏗️ Setting up application..."
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

echo "🔧 Creating systemd service..."
cat > /etc/systemd/system/cec-flipper.service << EOFINNER
[Unit]
Description=CEC Flipper Control
After=network.target

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

systemctl enable cec-flipper.service

CURRENT_USER=$(logname 2>/dev/null || echo "pi")
usermod -a -G dialout,tty $CURRENT_USER

echo "✅ Setup complete!"
echo "📌 UART enabled for Flipper communication"
echo "📌 HTTP server available on port 8080"
echo "🔄 Reboot required to enable UART"

read -p "Reboot now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  reboot
fi
