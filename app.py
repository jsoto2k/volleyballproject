import os
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request

app = Flask(__name__)

# Upload folder for site files 
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed file extensions for upload to site 
ALLOWED_EXTENSIONS = {'dvw'}

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///volleyball.db'
db = SQLAlchemy(app)

# Database Tables
# Stores information on each player uploaded from the team roster 
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    position = db.Column(db.String(80), nullable=False)
    number = db.Column(db.Integer, nullable=False)

# Stores information on each team uploaded to the database
class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    players = db.relationship('Player', backref='team', lazy=True)

# Stores information on each match uploaded to the database
class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    home_team = db.Column(db.String(80), nullable=False)
    away_team = db.Column(db.String(80), nullable=False)
    result = db.Column(db.String(80), nullable=False)


def parse_dvw_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Initialize variables to store extracted data
    home_team = ""
    away_team = ""
    #match_result = "Unknown"  
    home_players = []
    away_players = []

    # Parsing flags
    in_teams_section = False
    in_home_players_section = False
    in_away_players_section = False

    for line in lines:
        #Teams section within DVW File 
        if "[3TEAMS]" in line:
            in_teams_section = True
            continue
        # Home Team Section within DVW File
        if "[3PLAYERS-H]" in line:
            in_teams_section = False
            in_home_players_section = True
            continue
        # Away Team Section within DVW File
        if "[3PLAYERS-V]" in line:
            in_home_players_section = False
            in_away_players_section = True
            continue
        # When in Teams Section, extract team names for home and away teams 
        if in_teams_section:
            team_info = line.split(';')
            if not home_team:
                home_team = team_info[1]
            else:
                away_team = team_info[1]
                
        # When in Home or Away Teams Section, extract player information
        if in_home_players_section or in_away_players_section:
            player_info = line.split(';')
            player = {
                'number': int(player_info[1]),
                'name': player_info[5],
                'position': player_info[4] if player_info[4] else "Unknown"
            }
            if in_home_players_section:
                home_players.append(player)
            elif in_away_players_section:
                away_players.append(player)

    return home_team, away_team, home_players, away_players


# Function to check for valid file extension 
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route for the apps home page 
@app.route('/')
def home():
    return render_template('upload.html')

# Route to upload a file to the site 
@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if the post request has the file part
    if 'file' not in request.files:
        return 'No file part'
    
    file = request.files['file']
    
    # If user does not select file, browser also submits an empty part without filename 
    if file.filename == '':
        return 'No selected file'
    
    # If file is allowed, save it to the upload folder
    if file and allowed_file(file.filename):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        
        return 'File uploaded successfully'
    
    return 'Invalid file type'


if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
    app.run(debug=True)

 