import os
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import pandas as pd 
import seaborn as sns 
import numpy as np 
from datavolley import read_dv, pycourt, helpers

app = Flask(__name__)

# Upload folder for site files 
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configuration for SQL Alchemy
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///volleyball.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Tables
 # Stores information on each team uploaded to the database
class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    players = db.relationship('Player', backref='team', lazy=True)

# Stores information on each player uploaded from the team roster
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)

# Stores information on each match uploaded to the database
class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    home_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    visiting_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    date = db.Column(db.String(80), nullable=False)

# Store information on each play made during a match
class Play(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    skill = db.Column(db.String(80), nullable=False)
    attack_code = db.Column(db.String(80), nullable=False)
    start_position_x = db.Column(db.String(80), nullable=False)
    end_position_x = db.Column(db.String(80), nullable=False)
    start_position_y = db.Column(db.String(80), nullable=False)
    end_position_y = db.Column(db.String(80), nullable=False)
    # point = db.Column(db.Boolean, nullable=False)
    custom_code = db.Column(db.String(80), nullable=False)

# Function to check if the file is a dvw file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'dvw'


def parse_all_dvw_files():
    file_list = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.dvw')]
    
    # Function to process individual files: This function will return the plays, home team, visiting team, and match date
    def process_file(file_path):
        dv_instance = read_dv.DataVolley(os.path.join(UPLOAD_FOLDER, file_path))
        plays = dv_instance.get_plays()
        home_team = plays.iloc[0]['home_team']
        visiting_team = plays.iloc[0]['visiting_team']
        
        return plays, home_team, visiting_team, dv_instance.match_info['day'][0]

    # Loop through all the files in the upload folder and process them by assigning data to variables
    for file_name in file_list: 
        plays, home_team_name, visitng_team_name, match_date = process_file(file_name)
        
    # Adding data to the database 
    
        # Add home team info
        home_team = Team.query.filter_by(name=home_team_name).first()
        if not home_team :
            home_team = Team(name=home_team_name)
            db.session.add(home_team)
            db.session.commit()
        
        # Add visiting team info
        visiting_team = Team.query.filter_by(name=visitng_team_name).first()
        if not visiting_team:
            visiting_team = Team(name=visitng_team_name)
            db.session.add(visiting_team)
            db.session.commit()
        
        # Add match info
        match = Match.query.filter_by(home_team_id=home_team.id, visiting_team_id=visiting_team.id, date=match_date).first()
        if match: 
            continue
        match = Match(home_team_id=home_team.id, visiting_team_id=visiting_team.id, date=match_date)
        db.session.add(match)
        db.session.commit()
        
    # Add players 
        for _, play in plays.iterrows():
            player_name = play['player_name']
            if not player_name or not isinstance(player_name, str) or not isinstance(play['attack_code'], str) or np.isnan(play['start_coordinate_x']):
                continue
            team_id = home_team.id if play['team'] == 'home' else visiting_team.id
            player = Player.query.filter_by(name=player_name, team_id=team_id).first()
            if not player: 
                player = Player(name=player_name, team_id=team_id)
                db.session.add(player)
                db.session.commit()
            created_play = Play (
                match_id=match.id,
                team_id=team_id,
                player_id=player.id,
                skill=play['skill'],
                attack_code=play['attack_code'],
                start_position_x=play['start_coordinate_x'],
                end_position_x=play['end_coordinate_x'],
                start_position_y=play['start_coordinate_y'],
                end_position_y=play['end_coordinate_y'],
                custom_code=play['custom_code']
            )
            db.session.add(created_play)
            db.session.commit()
    
    



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
        
        # Parse the dvw file to get match and player information
        home_team, away_team, home_players, away_players = parse_dvw_file(file_path) 
        print (home_team, away_team, home_players, away_players)

        # # Store the teams in the database
        # home_team_entry = Team(name=home_team)
        # away_team_entry = Team(name=away_team)
        # db.session.add(home_team_entry)
        # db.session.add(away_team_entry)
        # db.session.commit()

        # # Store the players in the database
        # for player in home_players:
        #     player_entry = Player(name=player['name'], position=player['position'], number=player['number'], team_id=home_team_entry.id)
        #     db.session.add(player_entry)

        # for player in away_players:
        #     player_entry = Player(name=player['name'], position=player['position'], number=player['number'], team_id=away_team_entry.id)
        #     db.session.add(player_entry)

        # db.session.commit()

        # # Store the match in the database (result is "Unknown" for now)
        # match_entry = Match(home_team=home_team, away_team=away_team, result="Unknown")
        # db.session.add(match_entry)
        # db.session.commit()

        return 'File uploaded and data added to the database successfully'
    
    return 'Invalid file type'


if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
    app.run(debug=True)

 