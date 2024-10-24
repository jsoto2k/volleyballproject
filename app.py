import os
from flask_sqlalchemy import SQLAlchemy
from flask import Flask

app = Flask(__name__)

# Upload folder for site files 
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed file extensions for upload to site 
ALLOWED_EXTENSIONS = {'dvw'}

# Function to check for valid file extension 
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

