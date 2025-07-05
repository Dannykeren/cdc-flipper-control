#!/usr/bin/env python3
"""
Simple HTTP server for testing CEC commands from Mac
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import socket
import urllib.parse
import cec_control

def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

class CECHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse the URL
        parsed_path = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_path.query)
        
        # Get command from URL parameter
        command = query.get('cmd', [''])[0].upper()
        
        response = {"status": "error", "message": "Unknown command"}
        
        if command == "PING":
            response = {"status": "success", "message": "pong"}
        elif command == "SCAN":
            result = cec_control.scan_devices()
            response = {"status": "success", "command": "SCAN", "result": result}
        elif command == "POWER_ON":
            result = cec_control.power_on()
            response = {"status": "success", "command": "POWER_ON", "result": result}
        elif command == "POWER_OFF":
            result = cec_control.power_off()
            response = {"status": "success", "command": "POWER_OFF", "result": result}
        elif command == "STATUS":
            result = cec_control.get_power_status()
            response = {"status": "success", "command": "STATUS", "result": result}
        
        # Send response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response, indent=2).encode())

if __name__ == "__main__":
    server = HTTPServer(('0.0.0.0', 8080), CECHandler)
    print(f"HTTP CEC Test Server running on http://{get_ip_address()}:8080")
    print(f"Test with: curl 'http://{get_ip_address()}:8080?cmd=PING'")
    server.serve_forever()
