import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging
import mimetypes
import urllib
from urllib.parse import unquote_plus
import socket
import threading

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

UDP_IP = '127.0.0.1'
UDP_PORT = 5000
HTTP_PORT = 3000

class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('index.html')
        elif pr_url.path == '/Send message':
            self.send_html_file('Send message.html')
        else:
            if '.' in pr_url.path:
                self.send_static()
            else:
                self.send_html_file('error.html', 404)

    def do_POST(self):
        size = self.headers.get('Content-Length')
        print(size)
        data = self.rfile.read(int(size)).decode()
        print(data)
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.sendto(data.encode(), (UDP_IP, UDP_PORT))
        client_socket.close()
        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()


    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        if self.path == '/favicon.ico':
            self.send_response(404)
            self.end_headers()
            return
        
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'.{self.path}', 'rb') as file:
            self.wfile.write(file.read())


def save_data(data):
    client = MongoClient("mongodb://127.0.0.1:27017", server_api=ServerApi('1'))
    db = client.get_database('homework')
    parse_data = unquote_plus(data.decode())

    try:
        parse_data = {key: value for key, value in [el.split('=') for el in parse_data.split('&')]}
        parse_data['date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        db.messages.insert_one(parse_data)
    except ValueError as e:
        logging.error(f"Parse error: {e}")
    except Exception as e:
        logging.error(f"Error in saving data: {e}")
    finally:
        client.close()


def run_http_server(server_class=HTTPServer, handler_class=HttpHandler):
    server_address = ('', HTTP_PORT)
    http = server_class(server_address, handler_class)
    try:
        logging.info('Server started on port %d', HTTP_PORT)
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()

def run_socket_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    logging.info('Server started on UDP port %d', UDP_PORT)
    print("Socket started")
    
    try:
        while True:
            data, addr = sock.recvfrom(1024)
            logging.info('received %s bytes from %s', len(data), addr)
            save_data(data)
    except Exception as e:
        logging.error(e)
    finally:
        logging.info('shutting down')
        sock.close()

if __name__ == '__main__':
    http_thread = threading.Thread(target=run_http_server)
    socket_thread = threading.Thread(target=run_socket_server)
    
    http_thread.start()
    socket_thread.start()
    
    http_thread.join()
    socket_thread.join()
