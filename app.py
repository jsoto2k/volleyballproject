import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy import SQLAlchemy
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')  # Use non-interactive backend for server environments
import pandas as pd 
import seaborn as sns 
import numpy as np 
from datavolley import read_dv, pycourt, helpers
import webbrowser

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

    # Define relationships to Team
    home_team = db.relationship('Team', foreign_keys=[home_team_id], backref='home_matches')
    visiting_team = db.relationship('Team', foreign_keys=[visiting_team_id], backref='visiting_matches')
    origin_file = db.Column(db.String(255), nullable=True)


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

def is_valid_play(play):
    required_keys = ['player_name', 'attack_code', 'start_coordinate_x', 'end_coordinate_x']
    for key in required_keys:
        if key not in play or pd.isnull(play[key]):
            return False
    return True

def parse_all_dvw_files():
    problematic_files = []
    successful_files = []
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
        try: 
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
            match = Match(home_team_id=home_team.id, visiting_team_id=visiting_team.id, date=match_date, origin_file=file_name)
            db.session.add(match)
            db.session.commit()
            
        # Add players 
            for _, play in plays.iterrows():
                player_name = play['player_name']
                #Check if the play contains all necessary data
                if not is_valid_play(play):
                    continue
                
                # add player to the database
                team_id = home_team.id if play['team'] == home_team.name else visiting_team.id
                player = Player.query.filter_by(name=player_name, team_id=team_id).first()
                if not player: 
                    player = Player(name=player_name, team_id=team_id)
                    db.session.add(player)
                    db.session.commit()
                
                # add plays to the datagbase
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
        except Exception as e:
            problematic_files.append(file_name)
            print(f"Error processing file {file_name}: {e}")
    return problematic_files
                
    
def get_heatmap_data(team_id, skill=None, player_ids=None):
    query = Play.query.filter_by(team_id=team_id)
    if skill:
        query = query.filter_by(skill=skill)
    if player_ids:
        # Ensure player_ids is a list of integers
        player_ids = [int(pid) for pid in player_ids]
        query = query.filter(Play.player_id.in_(player_ids))
    return query.all()


def generate_attack_heatmap(data, title, filename):
    # Ensure the coordinates are numeric
    data['end_coordinate_x'] = pd.to_numeric(data['end_coordinate_x'], errors='coerce')
    data['end_coordinate_y'] = pd.to_numeric(data['end_coordinate_y'], errors='coerce')

    # Drop rows with missing or non-numeric coordinates
    data = data.dropna(subset=['end_coordinate_x', 'end_coordinate_y'])

    # Ensure static directory exists
    static_dir = 'static'
    os.makedirs(static_dir, exist_ok=True)

    # Generate heatmap
    fig, ax = plt.subplots()
    pycourt.pycourt(ax=ax)
    sns.kdeplot(
        x=data['end_coordinate_x'],
        y=data['end_coordinate_y'],
        ax=ax,
        cmap="YlOrRd",
        fill=True,
        alpha=0.5
    )
    plt.title(title)
    heatmap_path = os.path.join(static_dir, filename)
    plt.savefig(heatmap_path)
    plt.close()
    return f'static/{filename}'


# Route for the apps home page 
@app.route('/')
def home():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if the post request has the file part
    if 'files' not in request.files:
        return 'No files part'

    files = request.files.getlist('files')
    # If user does not select file, browser warns user
    if not files:
        return 'No files selected'

    # If file is not allowed or empty, browser warns user
    for file in files:
        if file.filename == '' or not allowed_file(file.filename):
            continue
   
    # If file is allowed, save it to the upload folder
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
    
    # Parse the dvw files to get match and player information
    problematic = parse_all_dvw_files()

    if problematic:
        # If we have any bad files, show them on a special page
        return render_template(
            'process_result.html',
            problematic_files=problematic
        )
    else:
        # Otherwise, carry on as normal
        return redirect(url_for('heatmaps'))

@app.route('/heatmaps')
def heatmaps():
    teams = Team.query.all()
    return render_template('heatmaps.html', teams=teams)

@app.route('/generate_heatmap', methods=['POST'])
def generate_heatmap():
    team_id = request.form.get('team_id')
    skill_filter = request.form.get('skill')
    player_ids = request.form.getlist('player_ids')

    team = Team.query.get(team_id)
    player_names = [Player.query.get(pid).name for pid in player_ids]
    players_string = ", ".join(player_names) if player_names else "All Players"

    filename = f"{team.name}_{'_'.join(player_names) if player_names else 'AllPlayers'}_heatmap.png".replace(" ", "_")

    plays = get_heatmap_data(team_id, skill_filter, player_ids)
    data = pd.DataFrame([{
        'end_coordinate_x': play.end_position_x,
        'end_coordinate_y': play.end_position_y
    } for play in plays])

    if data.empty:
        return "No data available for the selected filters.", 404

    heatmap_title = f"Heatmap for {team.name} - {players_string}"
    heatmap_path = generate_attack_heatmap(data, heatmap_title, filename)
    return render_template('heatmap_result.html', image_url=heatmap_path)

@app.route('/players/<int:team_id>')
def get_players_by_team(team_id):
    players = Player.query.filter_by(team_id=team_id).all()
    return jsonify([{'id': player.id, 'name': player.name} for player in players])
    
@app.route('/view_teams')
def view_teams():
    teams = Team.query.all()
    matches = Match.query.all()
    return render_template('view_teams.html', teams=teams, matches=matches)

@app.route('/delete_file/<filename>', methods=['POST'])
def delete_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # 1) Find all matches that originated from this file
    matches_from_file = Match.query.filter_by(origin_file=filename).all()
    for match in matches_from_file:
        # 2) Remove all plays belonging to this match
        Play.query.filter_by(match_id=match.id).delete()
        db.session.commit()

        # 3) Remove the match itself
        db.session.delete(match)
        db.session.commit()
    
    all_teams = Team.query.all()
    for team in all_teams:
        # Check if team has any existing matches (home or visiting)
        # or any players that appear in plays
        match_exists = (Match.query.filter((Match.home_team_id==team.id) | 
                                           (Match.visiting_team_id==team.id)).first())
        if not match_exists:
            # If no match references this team, check if it has any associated players left
            db_players = Player.query.filter_by(team_id=team.id).all()

            # if the team has no matches, remove the players
            if db_players:
                for p in db_players:
                    db.session.delete(p)
                db.session.commit()

            # Remove the team
            db.session.delete(team)
            db.session.commit()  
                  
    # Re-parse to see if any more problematic files remain
    problematic = parse_all_dvw_files()
    if problematic:
        return render_template(
            'process_result.html',
            problematic_files=problematic
        )
    else:
        return redirect(url_for('heatmaps'))

@app.route('/delete_all_files', methods=['POST'])
def delete_all_files():
    """
    Delete all problematic files in one go.
    """
    # Get the comma-separated string of files from the hidden form field
    problematic_str = request.form.get('problematic_files', '')
    if not problematic_str:
        # No files found, just redirect to parse again
        return redirect(url_for('parse_all_dvw_files'))  # or wherever you'd like

    files_to_delete = problematic_str.split(',')
    for filename in files_to_delete:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)

    # After deleting them all, re-parse or do whichever flow you prefer
    # Typically, we'd re-parse and either show if there's still more problematic
    new_problem_files = parse_all_dvw_files()  
    if new_problem_files:
        return render_template('process_result.html', problematic_files=new_problem_files)
    else:
        return redirect(url_for('heatmaps'))

@app.route('/manage_files')
def manage_files():
    # Gather all .dvw files in UPLOAD_FOLDER
    file_list = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.dvw')]
    
    return render_template('manage_files.html', files=file_list)

@app.route('/delete_selected_files', methods=['POST'])
def delete_selected_files():
    # 'files_to_delete' is a list of checkboxes from manage_files.html
    files_to_delete = request.form.getlist('files_to_delete')
    if not files_to_delete:
        # No files checked
        return redirect(url_for('manage_files'))
    
    for file_name in files_to_delete:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
        if os.path.exists(file_path):
            os.remove(file_path)

    # After deleting selected files, redirect back to the manage files page
    return redirect(url_for('manage_files'))




if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    url = "http://127.0.0.1:5000"

    # Only open the browser if this is the first process (not Flask's auto-reloader)
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        webbrowser.open_new(url)

    app.run(debug=True)

 