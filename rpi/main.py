#!/usr/bin/env python3
"""
CEC Flipper Control v3.0 - Clean Static Display Version
Field-ready solution with static ICSS branding
"""
import time
import logging
import sys
import signal
import json
import threading
import serial
import os
import subprocess
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main")

def execute_cec_command(command, vendor="Unknown", timeout=10):
    """Execute CEC command - clean and simple"""
    try:
        logger.info(f"Executing CEC command: {command}")
        
        process = subprocess.Popen(
            ['cec-client', '-s', '-d', '1'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        stdout, stderr = process.communicate(input=command + '\n', timeout=timeout)
        
        if process.returncode == 0:
            logger.info(f"✅ Command successful: {command}")
            return f"✅ Command executed: {command}"
        else:
            logger.error(f"❌ Command failed: {command} - {stderr}")
            return f"❌ Command failed: {stderr}"
            
    except subprocess.TimeoutExpired:
        process.kill()
        return f"❌ Command timed out: {command}"
    except Exception as e:
        return f"❌ Error executing command: {str(e)}"

class CECController:
    def __init__(self):
        self.running = False
        self.uart_serial = None
    
    def start_uart_interface(self):
        """Start UART interface for Flipper Zero"""
        try:
            self.uart_serial = serial.Serial('/dev/ttyAMA0', 115200, timeout=1)
            uart_thread = threading.Thread(target=self.uart_loop)
            uart_thread.daemon = True
            uart_thread.start()
            logger.info("UART interface started on /dev/ttyAMA0")
        except Exception as e:
            logger.error(f"Failed to start UART: {e}")
    
    def uart_loop(self):
        """Handle UART communication with Flipper"""
        while self.running:
            try:
                if self.uart_serial and self.uart_serial.in_waiting > 0:
                    line = self.uart_serial.readline().decode('utf-8').strip()
                    if line:
                        logger.info(f"UART received: '{line}'")
                        response = self.process_command(line)
                        if self.uart_serial:
                            self.uart_serial.write((response + '\n').encode('utf-8'))
                            logger.info(f"UART sent: {response}")
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"UART error: {e}")
                time.sleep(1)
    
    def process_command(self, command_json):
        """Process CEC command - clean and simple"""
        try:
            command = json.loads(command_json)
            cmd_type = command.get('command', '').upper()
            vendor = "Unknown"
            
            if cmd_type == 'PING':
                return json.dumps({"status": "success", "result": "pong"})
            
            elif cmd_type == 'SCAN':
                result = execute_cec_command("scan", "System", timeout=15)
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'STATUS':
                result = execute_cec_command("pow 0", "System", timeout=5)
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'CUSTOM':
                cec_command = command.get('cec_command', '')
                if cec_command:
                    # Simple vendor detection
                    if "4F:" in cec_command:
                        vendor = "Samsung"
                    elif "0F:" in cec_command:
                        vendor = "Samsung DB Series"
                    elif "10:" in cec_command:
                        vendor = "Generic/Projector"
                    
                    result = execute_cec_command(cec_command, vendor)
                    return json.dumps({"status": "success", "result": result})
                else:
                    return json.dumps({"status": "error", "result": "No CEC command provided"})
            
            # Direct power commands
            elif cmd_type == 'POWER_ON':
                result = execute_cec_command("on 0", vendor)
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'POWER_OFF':
                result = execute_cec_command("standby 0", vendor)
                return json.dumps({"status": "success", "result": result})
            
            # HDMI input switching
            elif cmd_type == 'HDMI_1':
                result = execute_cec_command("tx 4F:82:10:00", "Samsung")
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'HDMI_2':
                result = execute_cec_command("tx 4F:82:20:00", "Samsung")
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'HDMI_3':
                result = execute_cec_command("tx 4F:82:30:00", "Samsung")
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'HDMI_4':
                result = execute_cec_command("tx 4F:82:40:00", "Samsung")
                return json.dumps({"status": "success", "result": result})
            
            # Volume commands
            elif cmd_type == 'VOLUME_UP':
                result = execute_cec_command("volup", "Generic")
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'VOLUME_DOWN':
                result = execute_cec_command("voldown", "Generic")
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'MUTE':
                result = execute_cec_command("mute", "Generic")
                return json.dumps({"status": "success", "result": result})
            
            else:
                return json.dumps({"status": "error", "result": f"Unknown command: {cmd_type}"})
                
        except json.JSONDecodeError:
            return json.dumps({"status": "error", "result": "Invalid JSON"})
        except Exception as e:
            logger.error(f"Command processing error: {str(e)}")
            return json.dumps({"status": "error", "result": str(e)}")
    
    def run(self):
        """Main application loop"""
        self.running = True
        
        logger.info("🚀 ICSS CEC Controller v3.0 - Professional Field Tool")
        
        # Start UART interface
        self.start_uart_interface()
        
        logger.info("CEC Controller running with static ICSS display")
        
        # Keep running
        while self.running:
            time.sleep(1)
    
    def stop(self):
        """Stop all interfaces"""
        self.running = False
        if self.uart_serial:
            try:
                self.uart_serial.close()
            except:
                pass
        logger.info("CEC Controller stopped")

def signal_handler(sig, frame):
    global controller
    logger.info("Shutting down...")
    if 'controller' in globals():
        controller.stop()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    controller = CECController()
    
    try:
        controller.run()
    except KeyboardInterrupt:
        pass
    finally:
        controller.stop()
