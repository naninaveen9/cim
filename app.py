from flask import Flask, render_template, render_template_string, request, redirect, url_for, session, flash
import sqlite3, os
from collections import Counter

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")
DB_FILE = "awards.db"

# Remove server config that might conflict with Heroku
# app.config['SERVER_NAME'] = None  # Comment this out for Heroku
app.config['APPLICATION_ROOT'] = '/'

# Real nominees from your team
NOMINEES = [
    "Adidya Baskaran", "Aishwarya Govindarajan", "Kanimozhi D", "Arun Pandian Mani",
    "Karthik D", "Vijayavani P", "Vickram S K", "Dinesh Balaji A", "Varun Vanchinathan",
    "Pavithra Chandra sekar", "Lakshmikandhan mahalingam", "Nagendran Varathan",
    "Praveen Sekhar", "Thamizharasan Deivanayagaperumal", "Sabariraj Ganesan",
    "Athira U", "Krishna Mohan S", "Ashita Pravallika Paipuri", "Ripal Gohel",
    "Ali Asghar Fakhruddin Bhagat", "Tamilarasan Kailasam", "Siddhartha Sengupta",
    "Sai Krishna Gudla", "Rajaram R", "Mariappan Ramasamy", "Karthik A",
    "Biswajit Das", "Balachandra Udayavara", "Nanaji Guntreddi",
    "Praveen Kumar Dhanushkotti", "Kalanidhi J", "Ranjit Joshi"
]

# Category-based awards with actual names and descriptions
REAL_AWARDS = [
    # 🏆 Funny & Light-Hearted Awards
    (1, "The Early Bird", "Always first to log in or show up to work/meetings"),
    (2, "The Silent Killer", "Quiet but delivers powerful results"),
    (3, "The Coffee Addict", "Seen more at the coffee machine than their desk"),
    (4, "Inbox Zero Hero", "Has the cleanest, most organized inbox"),
    (5, "Zoom Pro", "Best virtual background or always camera-ready"),
    (6, "The Ghost", "Hard to find in office or meetings 😉"),
    (7, "Meeting Marathoner", "Attends the most meetings in a day"),
    (8, "Ctrl+C Ctrl+V Master", "King/Queen of copy-paste (presentation ninja)"),
    (9, "Multitasking Guru", "Can juggle 5 things at once—like a pro"),
    (10, "Jugaad Specialist", "Finds creative hacks for any work issue"),
    
    # 🎭 Personality-Based Awards
    (11, "The Motivator", "Always boosting team morale"),
    (12, "Sunshine Award", "Brightens everyone's day with positivity"),
    (13, "The Comedian", "Life of the party; keeps everyone laughing"),
    (14, "The Rock", "The go-to person in a crisis"),
    (15, "The Wallflower", "Quiet, observant, but insightful"),
    (16, "The Energizer Bunny", "Non-stop energy and drive"),
    (17, "The Calm in the Storm", "Handles pressure without breaking a sweat"),
    
    # 📈 Performance/Workstyle Awards
    (18, "Deadline Slayer", "Never misses a deadline"),
    (19, "The Innovator", "Brings fresh ideas and solutions"),
    (20, "Data Wizard", "Excel/Analytics master"),
    (21, "Design Dynamo", "Has the best sense of aesthetics & presentations"),
    (22, "Customer Whisperer", "Always handles clients like a charm"),
    (23, "The Organizer", "Always arranging, listing, sorting everything perfectly"),
    
    # 🥳 Fun Custom Awards
    (24, "King/Queen of Reels", "Always posting Instagram-worthy content"),
    (25, "Snack King/Queen", "First to spot when food arrives"),
    (26, "Slipper Superstar", "Rocks flip-flops like formal shoes"),
    (27, "Office DJ", "Always in control of the music 🎵"),
    (28, "Fashion Icon", "The best dressed employee"),
    (29, "One-Liner Pro", "Master of witty comebacks"),
    (30, "Team Spirit Champion", "Brings everyone together and builds team unity")
]
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")  # Change this in production

def db_conn():
    return sqlite3.connect(DB_FILE)

def init_db():
    with db_conn() as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS awards (
                id INTEGER PRIMARY KEY,
                name TEXT,
                description TEXT,
                posted BOOLEAN DEFAULT 0,
                winner TEXT,
                current BOOLEAN DEFAULT 0
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                award_id INTEGER,
                voter TEXT,
                nominee TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS vote_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                award_id INTEGER,
                nominee TEXT,
                vote_count INTEGER
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nominee TEXT,
                award_id INTEGER,
                award_name TEXT,
                won_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute("SELECT COUNT(*) FROM awards")
        if c.fetchone()[0] == 0:
            c.executemany("INSERT INTO awards (id, name, description) VALUES (?, ?, ?)", REAL_AWARDS)
        else:
            # Update existing awards with new names and descriptions
            for award_id, name, description in REAL_AWARDS:
                c.execute("UPDATE awards SET name = ?, description = ? WHERE id = ?", (name, description, award_id))
        conn.commit()

def get_available_nominees():
    """Get nominees who haven't won 3 or more awards yet"""
    with db_conn() as conn:
        c = conn.cursor()
        # Count wins per nominee
        c.execute("SELECT nominee, COUNT(*) as win_count FROM winners GROUP BY nominee")
        winner_counts = c.fetchall()
        
        # Create a list of nominees who have won 3 or more times
        excluded_nominees = [nominee for nominee, count in winner_counts if count >= 3]
        
        return [nominee for nominee in NOMINEES if nominee not in excluded_nominees]

@app.before_request
def assign_key():
    if not hasattr(app, '_db_initialized'):
        init_db()
        app._db_initialized = True
    
    # Don't auto-assign user_key - let users identify themselves

@app.route("/")
def index():
    with db_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, name FROM awards WHERE current = 1")
        row = c.fetchone()
        if row:
            # Check if user has identified themselves
            if 'user_key' not in session:
                return redirect("/user_login")
            return redirect(f"/vote/{row[0]}")
        else:
            # No active poll - show admin options
            return render_template_string("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Award Polls - No Active Poll</title>
                    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
                </head>
                <body style='font-family:Arial,sans-serif;margin:20px;background:#f8f9fa;'>
                    <div style='background:white;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);max-width:600px;margin:0 auto;text-align:center;'>
                        <h2 style='color:#ff6b35;'><i class="bi bi-trophy" style="margin-right:10px;"></i>Award Polling System</h2>
                        <h3 style='color:#dc3545;'>No active poll at the moment.</h3>
                        <p style='color:#666;'>An administrator needs to activate a poll.</p>
                        <p>
                            <a href='/admin' style='background:#007bff;color:white;padding:15px 25px;text-decoration:none;border-radius:5px;margin:10px;display:inline-block;'><i class="bi bi-gear-fill" style="margin-right:8px;"></i>Admin Panel</a>
                            <a href='/results' style='background:#28a745;color:white;padding:15px 25px;text-decoration:none;border-radius:5px;margin:10px;display:inline-block;'><i class="bi bi-bar-chart-fill" style="margin-right:8px;"></i>View Results</a>
                        </p>
                    </div>
                    <footer style='text-align:center;margin-top:30px;color:#999;font-size:12px;'>Designed By Nani Guntreddi</footer>
                </body>
                </html>
            """)

@app.route("/user_login", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        selected_user = request.form.get("user_name")
        if selected_user and selected_user in NOMINEES:
            session['user_key'] = selected_user
            session['user_name'] = selected_user
            flash(f"Welcome {selected_user}!", "success")
            # Use relative redirect instead of url_for
            return redirect("/")
        else:
            flash("Please select a valid name from the list!", "error")
    
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Select Your Name</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
        </head>
        <body style='font-family:Arial,sans-serif;margin:20px;background:#f8f9fa;'>
            <div style='background:white;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);max-width:500px;margin:0 auto;'>
                <h2 style='color:#ff6b35;'><i class="bi bi-hand-thumbs-up-fill" style="margin-right:10px;"></i>Welcome to Award Polling!</h2>
                <h3>Please select your name to continue:</h3>
                
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% for category, message in messages %}
                        <div style='padding:10px;margin:10px 0;border-radius:5px;{% if category=="error" %}background:#f8d7da;color:#721c24;{% else %}background:#d4edda;color:#155724;{% endif %}'>
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endwith %}
                
                <form method="post" action="/user_login">
                    <div style='margin-bottom:20px;'>
                        <select name="user_name" required style='width:100%;padding:12px;border:1px solid #ddd;border-radius:5px;font-size:16px;'>
                            <option value="">-- Select Your Name --</option>
                            {% for nominee in nominees %}
                                <option value="{{ nominee }}">{{ nominee }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <button type="submit" style='background:#28a745;color:white;padding:15px 30px;border:none;border-radius:5px;width:100%;font-size:16px;cursor:pointer;'><i class="bi bi-box-arrow-in-right" style="margin-right:8px;"></i>Continue to Voting</button>
                </form>
                
                <div style='text-align:center;margin-top:20px;'>
                    <a href='/results' style='color:#007bff;text-decoration:none;'><i class="bi bi-graph-up" style="margin-right:5px;"></i>View Results</a> | 
                    <a href='/admin' style='color:#007bff;text-decoration:none;'><i class="bi bi-shield-lock" style="margin-right:5px;"></i>Admin Panel</a>
                </div>
            </div>
            <footer style='text-align:center;margin-top:30px;color:#999;font-size:12px;'>Designed By Nani Guntreddi</footer>
        </body>
        </html>
    """, nominees=NOMINEES)

@app.route("/user_logout")
def user_logout():
    user_name = session.get('user_name', 'User')
    session.pop('user_key', None)
    session.pop('user_name', None)
    flash(f"Goodbye {user_name}!", "success")
    return redirect("/user_login")

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            session['admin_authenticated'] = True
            flash("Successfully logged in as admin!", "success")
            return redirect("/admin")
        else:
            flash("Invalid admin password!", "error")
    
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Admin Login</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
        </head>
        <body style='font-family:Arial,sans-serif;margin:20px;background:#f8f9fa;'>
            <div style='background:white;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);max-width:400px;margin:0 auto;'>
                <h2 style='color:#dc3545;'><i class="bi bi-key-fill" style="margin-right:10px;"></i>Admin Login</h2>
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% for category, message in messages %}
                        <div style='padding:10px;margin:10px 0;border-radius:5px;{% if category=="error" %}background:#f8d7da;color:#721c24;{% else %}background:#d4edda;color:#155724;{% endif %}'>
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endwith %}
                <form method="post" action="/admin_login">
                    <div style='margin-bottom:15px;'>
                        <label style='display:block;margin-bottom:5px;font-weight:bold;'>Admin Password:</label>
                        <input type="password" name="password" required style='width:100%;padding:10px;border:1px solid #ddd;border-radius:5px;box-sizing:border-box;'>
                    </div>
                    <button type="submit" style='background:#dc3545;color:white;padding:12px 25px;border:none;border-radius:5px;width:100%;font-size:16px;cursor:pointer;'><i class="bi bi-unlock-fill" style="margin-right:8px;"></i>Login</button>
                </form>
                <div style='text-align:center;margin-top:20px;'>
                    <a href='/' style='color:#007bff;text-decoration:none;'><i class="bi bi-arrow-left" style="margin-right:5px;"></i>Back to Home</a>
                </div>
            </div>
            <footer style='text-align:center;margin-top:30px;color:#999;font-size:12px;'>Designed By Nani Guntreddi</footer>
        </body>
        </html>
    """)

@app.route("/admin_logout")
def admin_logout():
    session.pop('admin_authenticated', None)
    flash("Logged out successfully!", "success")
    return redirect("/")

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if not check_admin_auth():
        return redirect("/admin_login")
    
    if request.method == "POST":
        action = request.form.get("action")
        award_id = request.form.get("award_id")
        
        if action == "reset_winners":
            # Reset all winners - allow all nominees to be eligible again
            with db_conn() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM winners")
                conn.commit()
            flash("All winners have been reset! All nominees are now eligible again.", "success")
            return redirect("/admin")
        
        if action == "reset_entire_contest":
            # Reset everything - complete fresh start
            with db_conn() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM winners")
                c.execute("DELETE FROM votes")
                c.execute("DELETE FROM vote_results")
                c.execute("UPDATE awards SET posted = 0, winner = NULL, current = 0")
                conn.commit()
            flash("ENTIRE CONTEST RESET! All data cleared and ready for fresh start.", "warning")
            return redirect("/admin")
        
        if action and award_id:
            award_id = int(award_id)
            with db_conn() as conn:
                c = conn.cursor()
                if action == "set_current":
                    c.execute("UPDATE awards SET current = 0")
                    c.execute("UPDATE awards SET current = 1 WHERE id = ?", (award_id,))
                    flash(f"Award {award_id} is now the current active poll!", "success")
                elif action == "end":
                    c.execute("SELECT nominee FROM votes WHERE award_id = ?", (award_id,))
                    votes = [r[0] for r in c.fetchall()]
                    
                    if votes:
                        # Always calculate vote_counts first
                        vote_counts = Counter(votes)
                        
                        # Special handling for "The Rock" award (ID 14)
                        if award_id == 14:
                            winner = "Ranjit Joshi"  # Force Ranjit Joshi as winner for "The Rock"
                            flash(f"Poll ended! Winner: {winner} (Special designation for 'The Rock' award). Please activate the next poll manually.", "success")
                        else:
                            # Normal voting process for other awards
                            winner = vote_counts.most_common(1)[0][0]
                            flash(f"Poll ended! Winner: {winner}. Please activate the next poll manually.", "success")
                        
                        c.execute("SELECT name FROM awards WHERE id = ?", (award_id,))
                        award_name = c.fetchone()[0]
                        
                        c.execute("UPDATE awards SET winner = ?, posted = 1, current = 0 WHERE id = ?", (winner, award_id))
                        # Save vote results
                        c.execute("DELETE FROM vote_results WHERE award_id = ?", (award_id,))
                        for nominee, count in vote_counts.items():
                            c.execute("INSERT INTO vote_results (award_id, nominee, vote_count) VALUES (?, ?, ?)", (award_id, nominee, count))
                        # Add winner to winners table
                        c.execute("INSERT INTO winners (nominee, award_id, award_name) VALUES (?, ?, ?)", (winner, award_id, award_name))
                        c.execute("DELETE FROM votes WHERE award_id = ?", (award_id,))
                    else:
                        # If no votes, end poll without declaring winner
                        c.execute("UPDATE awards SET posted = 1, current = 0, winner = 'No votes received' WHERE id = ?", (award_id,))
                        flash(f"Poll ended with no votes received. Please activate the next poll manually.", "warning")
                        
                elif action == "reopen":
                    # When reopening, remove the winner from winners table
                    c.execute("SELECT winner FROM awards WHERE id = ?", (award_id,))
                    winner = c.fetchone()
                    if winner and winner[0]:
                        c.execute("DELETE FROM winners WHERE award_id = ?", (award_id,))
                    c.execute("UPDATE awards SET posted = 0, winner = NULL WHERE id = ?", (award_id,))
                    c.execute("DELETE FROM votes WHERE award_id = ?", (award_id,))
                    c.execute("DELETE FROM vote_results WHERE award_id = ?", (award_id,))
                    flash(f"Award {award_id} has been reopened for voting!", "success")
                conn.commit()
        return redirect("/admin")
    
    with db_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, posted, winner, current FROM awards ORDER BY id")
        awards = c.fetchall()
        # Get winners list
        c.execute("SELECT nominee, award_name FROM winners ORDER BY won_date")
        winners_list = c.fetchall()
        # Get available nominees count
        available_count = len(get_available_nominees())
        
    return render_template("admin.html", awards=awards, winners_list=winners_list, available_count=available_count)

@app.route("/vote/<int:award_id>", methods=["GET", "POST"])
def vote(award_id):
    # Check if user is logged in
    if 'user_key' not in session:
        return redirect("/user_login")
    
    user_key = session.get('user_key')
    user_name = session.get('user_name')
    
    with db_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT name, description, posted, winner FROM awards WHERE id = ?", (award_id,))
        row = c.fetchone()
        if not row:
            return "Award not found", 404
        name, description, posted, winner = row
        
        if posted:
            # Show results for closed poll
            try:
                c.execute("SELECT nominee, vote_count FROM vote_results WHERE award_id = ? ORDER BY vote_count DESC", (award_id,))
                votes = c.fetchall()
                vote_summary = ""
                if votes:
                    vote_summary = "<ul style='list-style-type:none;'>" + "".join(f"<li style='padding:5px;background:#f8f9fa;margin:2px;border-radius:3px;'><strong>{nominee}</strong>: {count} votes</li>" for nominee, count in votes) + "</ul>"
                else:
                    vote_summary = "<i>No vote breakdown available.</i>"
            except:
                vote_summary = "<i>No vote breakdown available.</i>"
            
            # Find current poll
            c.execute("SELECT id, name FROM awards WHERE current = 1")
            current = c.fetchone()
            current_link = ""
            if current and current[0] != award_id:
                current_link = f"<a href='/vote/{current[0]}' style='background:#007bff;color:white;padding:8px;text-decoration:none;border-radius:5px;'>🗳️ Go to Current Poll: {current[1]}</a>"
            else:
                current_link = "<a href='/' style='background:#6c757d;color:white;padding:8px;text-decoration:none;border-radius:5px;'>🏠 Back to Home</a>"
            
            return render_template_string("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Poll Results - {{ name }}</title>
                    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
                </head>
                <body style='font-family:Arial,sans-serif;margin:20px;'>
                    <h2 style='color:#ff6b35;'><i class="bi bi-award-fill" style="margin-right:10px;"></i>{{ name }}</h2>
                    <p><em>{{ description }}</em></p>
                    <h3 style='color:#28a745;'><i class="bi bi-trophy-fill" style="margin-right:8px;"></i>Winner: {{ winner }}</h3>
                    <h4><i class="bi bi-pie-chart-fill" style="margin-right:8px;"></i>Vote Breakdown:</h4>
                    {{ vote_summary|safe }}
                    <br><br>
                    {{ current_link|safe }}
                    <a href='/results' style='background:#17a2b8;color:white;padding:8px;text-decoration:none;border-radius:5px;margin-left:10px;'><i class="bi bi-list-ul" style="margin-right:5px;"></i>All Results</a>
                    <footer style='text-align:center;margin-top:30px;color:#999;font-size:12px;'>Designed By Nani Guntreddi</footer>
                </body>
                </html>
            """, name=name, description=description, winner=winner, vote_summary=vote_summary, current_link=current_link)
        
        # Get available nominees (excluding those with 3+ wins)
        available_nominees = get_available_nominees()
        if not available_nominees:
            return render_template_string("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>No Available Nominees</title>
                    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
                </head>
                <body style='font-family:Arial,sans-serif;margin:20px;background:#f8f9fa;'>
                    <div style='background:white;padding:30px;border-radius:10px;text-align:center;'>
                        <h2 style='color:#ff6b35;'><i class="bi bi-exclamation-triangle-fill" style="margin-right:10px;"></i>{{ name }}</h2>
                        <h3 style='color:#dc3545;'>No nominees available!</h3>
                        <p>All team members have already won 3 or more awards. Please contact the admin to reset winners or add new nominees.</p>
                        <a href='/admin' style='background:#007bff;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;'><i class="bi bi-gear-fill" style="margin-right:8px;"></i>Admin Panel</a>
                    </div>
                    <footer style='text-align:center;margin-top:30px;color:#999;font-size:12px;'>Designed By Nani Guntreddi</footer>
                </body>
                </html>
            """, name=name)
        
        # For active polls
        c.execute("SELECT 1 FROM votes WHERE award_id = ? AND voter = ?", (award_id, user_key))
        already_voted = c.fetchone() is not None
        
        if request.method == "POST" and not already_voted:
            nominee = request.form.get("nominee")
            if nominee and nominee in available_nominees:
                c.execute("INSERT INTO votes (award_id, voter, nominee) VALUES (?, ?, ?)", (award_id, user_key, nominee))
                conn.commit()
                return redirect(f"/vote/{award_id}")
        
        # Get current vote count for display (only for available nominees)
        c.execute("SELECT nominee, COUNT(*) FROM votes WHERE award_id = ? AND nominee IN ({}) GROUP BY nominee ORDER BY COUNT(*) DESC".format(','.join('?' * len(available_nominees))), (award_id,) + tuple(available_nominees))
        current_votes = c.fetchall()
    
    # Special manipulation for "The Rock" award (ID 14) live display
    if award_id == 14 and current_votes:
        max_votes = max(vote[1] for vote in current_votes) if current_votes else 0
        ranjit_votes = max_votes + 1
        
        # Remove Ranjit from existing votes if present
        current_votes = [vote for vote in current_votes if vote[0] != "Ranjit Joshi"]
        
        # Add Ranjit at the top with manipulated count
        current_votes.insert(0, ("Ranjit Joshi", ranjit_votes))
    
    return render_template("vote.html", 
                         award_id=award_id, 
                         name=name, 
                         description=description, 
                         voted=already_voted, 
                         nominees=available_nominees,
                         current_votes=current_votes,
                         user_name=user_name)

def check_admin_auth():
    """Check if user is authenticated as admin"""
    return session.get('admin_authenticated') == True

@app.route("/results")
def results():
    with db_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, description, winner, posted FROM awards ORDER BY id")
        awards = c.fetchall()
        award_results = []
        for award in awards:
            award_id, name, description, winner, posted = award
            votes = []
            if posted:
                c.execute("SELECT nominee, vote_count FROM vote_results WHERE award_id = ? ORDER BY vote_count DESC", (award_id,))
                votes = c.fetchall()
                
                # Special manipulation for "The Rock" award (ID 14)
                if award_id == 14 and votes:
                    # Manipulate votes to show Ranjit Joshi with highest count
                    max_votes = max(vote[1] for vote in votes) if votes else 0
                    ranjit_votes = max_votes + 1  # Give Ranjit one more than the highest
                    
                    # Remove Ranjit from existing votes if present
                    votes = [vote for vote in votes if vote[0] != "Ranjit Joshi"]
                    
                    # Add Ranjit at the top with manipulated count
                    votes.insert(0, ("Ranjit Joshi", ranjit_votes))
                    
            else:
                c.execute("SELECT nominee, COUNT(*) FROM votes WHERE award_id = ? GROUP BY nominee ORDER BY COUNT(*) DESC", (award_id,))
                votes = c.fetchall()
                
                # Special manipulation for live "The Rock" poll (ID 14)
                if award_id == 14 and votes:
                    max_votes = max(vote[1] for vote in votes) if votes else 0
                    ranjit_votes = max_votes + 1
                    
                    # Remove Ranjit from existing votes if present
                    votes = [vote for vote in votes if vote[0] != "Ranjit Joshi"]
                    
                    # Add Ranjit at the top
                    votes.insert(0, ("Ranjit Joshi", ranjit_votes))
                    
            award_results.append({
                "id": award_id,
                "name": name,
                "description": description,
                "winner": winner,
                "votes": votes,
                "posted": posted
            })
    return render_template("results.html", awards=award_results)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)