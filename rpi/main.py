#!/usr/bin/env python3
"""
CEC Flipper Control - Main Application
"""
import serial
import json
import time
import logging
import sys
import signal
import cec_control

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

class CECHandler:
    def __init__(self, device="/dev/ttyGS0"):
        self.device = device
        self.serial_conn = None
        self.running = False
        
    def connect(self):
        """Connect to USB serial device"""
        try:
            self.serial_conn = serial.Serial(self.device, 115200, timeout=1)
            logger.info(f"Connected to {self.device}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {self.device}: {e}")
            return False
    
    def send_response(self, response):
        """Send JSON response"""
        try:
            json_response = json.dumps(response) + "\n"
            self.serial_conn.write(json_response.encode())
            logger.info(f"Sent: {response}")
        except Exception as e:
            logger.error(f"Failed to send response: {e}")
    
    def process_command(self, line):
        """Process incoming JSON command"""
        try:
            data = json.loads(line.strip())
            command = data.get("command", "").upper()
            
            logger.info(f"Processing: {command}")
            
            if command == "PING":
                self.send_response({
                    "command": "PING",
                    "status": "pong", 
                    "timestamp": time.time()
                })
            elif command == "POWER_ON":
                result = cec_control.power_on()
                self.send_response({
                    "command": "POWER_ON",
                    "status": "success",
                    "result": result
                })
            elif command == "POWER_OFF":
                result = cec_control.power_off()
                self.send_response({
                    "command": "POWER_OFF",
                    "status": "success", 
                    "result": result
                })
            elif command == "SCAN":
                result = cec_control.scan_devices()
                self.send_response({
                    "command": "SCAN",
                    "status": "success",
                    "result": result
                })
            elif command == "STATUS":
                result = cec_control.get_power_status()
                self.send_response({
                    "command": "STATUS",
                    "status": "success",
                    "result": result
                })
            elif command == "CUSTOM":
                cec_cmd = data.get("cec_command", "")
                result = cec_control.send_custom_command(cec_cmd)
                self.send_response({
                    "command": "CUSTOM",
                    "status": "success",
                    "cec_command": cec_cmd,
                    "result": result
                })
            else:
                self.send_response({
                    "command": command,
                    "status": "error",
                    "message": f"Unknown command: {command}"
                })
                
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            self.send_response({
                "status": "error",
                "message": str(e)
            })
    
    def run(self):
        """Main loop"""
        if not self.connect():
            return False
            
        self.running = True
        
        self.send_response({
            "status": "ready",
            "message": "CEC Flipper Control ready"
        })
        
        logger.info("Listening for commands...")
        
        while self.running:
            try:
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode().strip()
                    if line:
                        self.process_command(line)
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(1)
        
        return True
    
    def stop(self):
        """Stop the handler"""
        self.running = False
        if self.serial_conn:
            self.serial_conn.close()

def signal_handler(sig, frame):
    global handler
    logger.info("Shutting down...")
    if 'handler' in globals():
        handler.stop()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    handler = CECHandler()
    
    try:
        handler.run()
    except KeyboardInterrupt:
        pass
    finally:
        handler.stop()
