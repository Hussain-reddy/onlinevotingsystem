from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "online-voting-secret-key"

DATABASE = "voting.db"


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            has_voted INTEGER DEFAULT 0
        )
    """)

    # Candidates table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            party TEXT NOT NULL,
            votes INTEGER DEFAULT 0
        )
    """)

    # Add sample candidates only if table is empty
    cursor.execute("SELECT COUNT(*) FROM candidates")
    count = cursor.fetchone()[0]

    if count == 0:
        candidates = [
            ("Candidate A", "Party A"),
            ("Candidate B", "Party B"),
            ("Candidate C", "Party C"),
            ("Candidate D", "Party D")
        ]

        cursor.executant(
            "INSERT INTO candidates (name, party) VALUES (?, ?)",
            candidates
        )

    conn.commit()
    conn.close()


# ---------------- HOME ----------------

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("vote"))

    return redirect(url_for("login"))


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if not username or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "error")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        conn = get_db()

        try:
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_password)
            )

            conn.commit()
            flash("Registration successful. Please login.", "success")

        except sqlite3.IntegrityError:
            flash("Username already exists.", "error")

        finally:
            conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect(url_for("vote"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


# ---------------- VOTING PAGE ----------------

@app.route("/vote")
def vote():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    candidates = conn.execute(
        "SELECT * FROM candidates"
    ).fetchall()

    conn.close()

    return render_template(
        "vote.html",
        user=user,
        candidates=candidates
    )


# ---------------- SUBMIT VOTE ----------------

@app.route("/submit_vote", methods=["POST"])
def submit_vote():

    if "user_id" not in session:
        return redirect(url_for("login"))

    candidate_id = request.form.get("candidate")

    if not candidate_id:
        flash("Please select a candidate.", "error")
        return redirect(url_for("vote"))

    conn = get_db()

    # Check whether user has already voted
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    if user["has_voted"] == 1:
        conn.close()
        flash("You have already voted.", "error")
        return redirect(url_for("results"))

    # Check candidate exists
    candidate = conn.execute(
        "SELECT * FROM candidates WHERE id = ?",
        (candidate_id,)
    ).fetchone()

    if not candidate:
        conn.close()
        flash("Invalid candidate.", "error")
        return redirect(url_for("vote"))

    # Update candidate vote
    conn.execute(
        "UPDATE candidates SET votes = votes + 1 WHERE id = ?",
        (candidate_id,)
    )

    # Mark user as voted
    conn.execute(
        "UPDATE users SET has_voted = 1 WHERE id = ?",
        (session["user_id"],)
    )

    conn.commit()
    conn.close()

    flash("Your vote has been submitted successfully!", "success")

    return redirect(url_for("results"))


# ---------------- RESULTS ----------------

@app.route("/results")
def results():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    candidates = conn.execute("""
        SELECT * FROM candidates
        ORDER BY votes DESC
    """).fetchall()

    total_votes = conn.execute(
        "SELECT SUM(votes) FROM candidates"
    ).fetchone()[0]

    conn.close()

    if total_votes is None:
        total_votes = 0

    return render_template(
        "results.html",
        candidates=candidates,
        total_votes=total_votes
    )


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)