# -*- coding: utf-8 -*-
"""
Created on Sat Dec  7 17:27:34 2024

@author: neell
"""

import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Change directory to the project folder
os.chdir(r"C:\Users\neell\Downloads\Academic Website\templates")

# Start the server
httpd = HTTPServer(('localhost', 8000), SimpleHTTPRequestHandler)
print("Serving at port 8000...")
httpd.serve_forever()