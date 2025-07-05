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

if ! grep -q "^dtoverlay=dwc2" /boot/config.txt; then
  echo "dtoverlay=dwc2" >> /boot/config.txt
fi

if ! grep -q "^libcomposite" /etc/modules; then
  echo "libcomposite" >> /etc/modules
fi

INSTALL_DIR="/opt/cec-flipper"
mkdir -p $INSTALL_DIR

python3 -m venv $INSTALL_DIR/venv
source $INSTALL_DIR/venv/bin/activate
pip install pyserial

cat > /usr/local/bin/setup-usb-gadget.sh << 'EOF'
#!/bin/bash
cd /sys/kernel/config/usb_gadget/
mkdir -p cec_flipper 2>/dev/null || true
cd cec_flipper

echo 0x1d6b > idVendor
echo 0x0104 > idProduct
echo 0x0100 > bcdDevice
echo 0x0200 > bcdUSB

mkdir -p strings/0x409
echo "CEC Flipper" > strings/0x409/manufacturer
echo "RPi CEC Interface" > strings/0x409/product
echo "001" > strings/0x409/serialnumber

mkdir -p configs/c.1/strings/0x409
echo "CEC Config" > configs/c.1/strings/0x409/configuration
echo 250 > configs/c.1/MaxPower

mkdir -p functions/acm.usb0
ln -sf functions/acm.usb0 configs/c.1/ 2>/dev/null || true

ls /sys/class/udc > UDC 2>/dev/null || true

sleep 2
if [ -e /dev/ttyGS0 ]; then
    chmod 666 /dev/ttyGS0
fi
EOF

chmod +x /usr/local/bin/setup-usb-gadget.sh

# Get repo info for downloading files
REPO_URL=$(curl -s "https://api.github.com/repos/$(whoami)/cec-flipper-control" 2>/dev/null | grep -o '"clone_url": "[^"]*' | cut -d'"' -f4 | sed 's/\.git$//' | sed 's/https:\/\/github.com\///')

if [ -n "$REPO_URL" ]; then
    curl -sSL "https://raw.githubusercontent.com/$REPO_URL/main/rpi/cec_control.py" > $INSTALL_DIR/cec_control.py
    curl -sSL "https://raw.githubusercontent.com/$REPO_URL/main/rpi/main.py" > $INSTALL_DIR/main.py
else
    echo "Could not determine repository URL. Please download files manually."
    exit 1
fi

chmod +x $INSTALL_DIR/main.py

cat > /etc/systemd/system/usb-gadget.service << 'EOF'
[Unit]
Description=Setup USB Gadget for CEC Control
After=local-fs.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/setup-usb-gadget.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/cec-flipper.service << EOF
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
EOF

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
