# -*- coding: utf-8 -*-
"""
Created on Mon Dec 22 21:10:45 2025

@author: nlal
"""

import os
import json

BASE_DIR = "Attachments/photos"

photo_data = {}

for folder in os.listdir(BASE_DIR):
    folder_path = os.path.join(BASE_DIR, folder)
    if os.path.isdir(folder_path):
        images = [
            f for f in os.listdir(folder_path)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
        ]
        if images:
            photo_data[folder] = images

output_path = os.path.join(BASE_DIR, "photos.json")
with open(output_path, "w") as f:
    json.dump(photo_data, f, indent=2)

print("photos.json generated successfully.")
