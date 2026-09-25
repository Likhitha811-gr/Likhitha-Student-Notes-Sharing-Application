from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import mysql.connector
import os
from werkzeug.utils import secure_filename

app = Flask(
    __name__,
    static_folder="templates/static",
    template_folder="templates"
)

app.secret_key = "change-this-secret-key"

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="student_notes_db"
    )


def setup_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploaded_notes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            subject VARCHAR(255) NOT NULL,
            filename VARCHAR(255) NOT NULL,
            description TEXT,
            uploaded_by VARCHAR(255),
            uploaded_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    cursor.execute("SHOW COLUMNS FROM uploaded_notes")
    columns = [row[0] for row in cursor.fetchall()]

    if "description" not in columns:
        cursor.execute("""
            ALTER TABLE uploaded_notes
            ADD COLUMN description TEXT
        """)

    if "uploaded_by" not in columns:
        cursor.execute("""
            ALTER TABLE uploaded_notes
            ADD COLUMN uploaded_by VARCHAR(255)
        """)

    if "uploaded_date" not in columns:
        cursor.execute("""
            ALTER TABLE uploaded_notes
            ADD COLUMN uploaded_date DATETIME DEFAULT CURRENT_TIMESTAMP
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favourites (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            note_id INT NOT NULL,
            UNIQUE(user_id, note_id)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


setup_database()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if password != confirm_password:
            return "Passwords do not match."

        name = first_name

        if last_name:
            name = first_name + " " + last_name

        if not name:
            name = username

        if not email or not password:
            return "Email and password are required."

        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id FROM users WHERE email = %s",
                (email,)
            )

            existing_user = cursor.fetchone()

            if existing_user:
                return "Email already registered."

            cursor.execute("""
                INSERT INTO users
                (name, email, password, role)
                VALUES (%s, %s, %s, %s)
            """, (
                name,
                email,
                password,
                "student"
            ))

            conn.commit()

            return render_template("success.html")

        except mysql.connector.Error as e:
            return "Database error: " + str(e)

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            return "Please enter email and password."

        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT id, name, email, password, role
                FROM users
                WHERE email = %s
            """, (email,))

            user = cursor.fetchone()

            if user and str(user["password"]) == str(password):

                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                session["user_email"] = user["email"]
                session["user_role"] = user["role"]

                return redirect(url_for("dashboard"))

            return "Invalid email or password."

        except mysql.connector.Error as e:
            return "Database error: " + str(e)

        finally:
            if cursor:
                cursor.close()

            if conn:
                conn.close()

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM uploaded_notes
        ORDER BY uploaded_date DESC
    """)

    notes = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM uploaded_notes
    """)

    total_notes = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM uploaded_notes
        WHERE uploaded_by = %s
    """, (session["user_name"],))

    my_uploads = cursor.fetchone()["total"]

    favourite_ids = set()

    cursor.execute("""
        SELECT note_id
        FROM favourites
        WHERE user_id = %s
    """, (session["user_id"],))

    favourite_rows = cursor.fetchall()

    for row in favourite_rows:
        favourite_ids.add(row["note_id"])

    cursor.close()
    conn.close()

    return render_template(
        "dashboard.html",
        user_name=session["user_name"],
        notes=notes,
        total_notes=total_notes,
        my_uploads=my_uploads,
        favourite_ids=favourite_ids
    )


@app.route("/upload", methods=["GET", "POST"])
def upload():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        subject = request.form.get("subject", "").strip()
        description = request.form.get("description", "").strip()

        file = request.files.get("file")

        if not title or not subject:
            return "Please enter title and subject."

        if not file or file.filename == "":
            return "Please select a file."

        filename = secure_filename(file.filename)

        file.save(
            os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )
        )

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO uploaded_notes
            (
                title,
                subject,
                filename,
                description,
                uploaded_by,
                uploaded_date
            )
            VALUES
            (%s, %s, %s, %s, %s, NOW())
        """, (
            title,
            subject,
            filename,
            description,
            session["user_name"]
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("upload.html")


@app.route("/view/<filename>")
def view(filename):

    if "user_id" not in session:
        return redirect(url_for("login"))

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


@app.route("/download/<filename>")
def download(filename):

    if "user_id" not in session:
        return redirect(url_for("login"))

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename,
        as_attachment=True
    )


@app.route("/favourite/<int:note_id>")
def favourite(note_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM favourites
        WHERE user_id = %s
        AND note_id = %s
    """, (
        session["user_id"],
        note_id
    ))

    existing = cursor.fetchone()

    if existing:

        cursor.execute("""
            DELETE FROM favourites
            WHERE user_id = %s
            AND note_id = %s
        """, (
            session["user_id"],
            note_id
        ))

    else:

        cursor.execute("""
            INSERT INTO favourites
            (user_id, note_id)
            VALUES (%s, %s)
        """, (
            session["user_id"],
            note_id
        ))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for("dashboard"))


@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM users
        WHERE id = %s
    """, (session["user_id"],))

    user = cursor.fetchone()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM uploaded_notes
        WHERE uploaded_by = %s
    """, (session["user_name"],))

    total_uploads = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM favourites
        WHERE user_id = %s
    """, (session["user_id"],))

    total_favourites = cursor.fetchone()["total"]

    cursor.close()
    conn.close()

    return render_template(
        "profile.html",
        user=user,
        total_uploads=total_uploads,
        total_favourites=total_favourites
    )


@app.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()

        if not name or not email:
            return "Name and email are required."

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE users
            SET name = %s,
                email = %s
            WHERE id = %s
        """, (
            name,
            email,
            session["user_id"]
        ))

        conn.commit()

        cursor.close()
        conn.close()

        session["user_name"] = name
        session["user_email"] = email

        return redirect(url_for("profile"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM users
        WHERE id = %s
    """, (session["user_id"],))

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "edit_profile.html",
        user=user
    )


@app.route("/change-password", methods=["GET", "POST"])
def change_password():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        current_password = request.form.get(
            "current_password",
            ""
        )

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if new_password != confirm_password:
            return "New passwords do not match."

        if len(new_password) < 12:
            return "Password must contain at least 12 characters."

        if not any(c.isupper() for c in new_password):
            return "Password must contain an uppercase letter."

        if not any(c.islower() for c in new_password):
            return "Password must contain a lowercase letter."

        if not any(c.isdigit() for c in new_password):
            return "Password must contain a number."

        if not any(not c.isalnum() for c in new_password):
            return "Password must contain a special character."

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT password
            FROM users
            WHERE id = %s
        """, (session["user_id"],))

        user = cursor.fetchone()

        if not user or str(user["password"]) != str(current_password):

            cursor.close()
            conn.close()

            return "Current password is incorrect."

        cursor.execute("""
            UPDATE users
            SET password = %s
            WHERE id = %s
        """, (
            new_password,
            session["user_id"]
        ))

        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for("profile"))

    return render_template("change_password.html")


@app.route("/edit-note/<int:note_id>", methods=["GET", "POST"])
def edit_note(note_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM uploaded_notes
        WHERE id = %s
        AND uploaded_by = %s
    """, (
        note_id,
        session["user_name"]
    ))

    note = cursor.fetchone()

    if not note:

        cursor.close()
        conn.close()

        return "You are not allowed to edit this note."

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        subject = request.form.get(
            "subject",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        if not title or not subject:

            cursor.close()
            conn.close()

            return "Title and subject are required."

        cursor.execute("""
            UPDATE uploaded_notes
            SET title = %s,
                subject = %s,
                description = %s
            WHERE id = %s
            AND uploaded_by = %s
        """, (
            title,
            subject,
            description,
            note_id,
            session["user_name"]
        ))

        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for("dashboard"))

    cursor.close()
    conn.close()

    return render_template(
        "edit_note.html",
        note=note
    )


@app.route("/delete-note/<int:note_id>", methods=["POST"])
def delete_note(note_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM uploaded_notes
        WHERE id = %s
        AND uploaded_by = %s
    """, (
        note_id,
        session["user_name"]
    ))

    note = cursor.fetchone()

    if not note:

        cursor.close()
        conn.close()

        return "You are not allowed to delete this note."

    cursor.execute("""
        DELETE FROM favourites
        WHERE note_id = %s
    """, (note_id,))

    cursor.execute("""
        DELETE FROM uploaded_notes
        WHERE id = %s
        AND uploaded_by = %s
    """, (
        note_id,
        session["user_name"]
    ))

    conn.commit()

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        note["filename"]
    )

    if os.path.exists(file_path):
        os.remove(file_path)

    cursor.close()
    conn.close()

    return redirect(url_for("dashboard"))


def local_summarize(text):
    import re
    from collections import Counter

    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    if not sentences:
        return "Please enter your study notes first."

    if len(sentences) <= 3:
        return "### Summary\n\n" + "\n\n".join(
            "• " + s.strip() for s in sentences if s.strip()
        )

    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    stop_words = {
        "the", "and", "for", "are", "with", "that", "this",
        "from", "have", "has", "was", "were", "into", "their",
        "they", "them", "also", "which", "will", "can", "been",
        "being", "about", "there", "these", "those", "than",
        "then", "when", "where", "what", "how", "why", "your", "you"
    }
    frequency = Counter(w for w in words if w not in stop_words)

    scored = []
    for index, sentence in enumerate(sentences):
        sw = re.findall(r'\b[a-zA-Z]{3,}\b', sentence.lower())
        score = sum(frequency.get(w, 0) for w in sw)
        scored.append((score, index, sentence.strip()))

    top = sorted(scored, reverse=True)[:5]
    top = sorted(top, key=lambda x: x[1])

    return "### Summary\n\n" + "\n\n".join(
        "• " + sentence for _, _, sentence in top if sentence
    )


def local_questions(text):
    import re
    sentences = [
        s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip())
        if s.strip()
    ]
    if not sentences:
        return "Please enter your study notes first."

    result = "### Short-answer questions\n\n"
    for i, sentence in enumerate(sentences[:5], 1):
        words = sentence.split()
        topic = " ".join(words[:8]).rstrip(".,!?")
        result += f"{i}. Explain the following concept: {topic}.\n\n"

    result += "### Important questions\n\n"
    for i, sentence in enumerate(sentences[:5], 1):
        result += f"{i}. What is the main idea explained in this statement?\n"
        result += f"   {sentence}\n\n"

    return result


def local_quiz(text):
    import re
    sentences = [
        s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip())
        if s.strip()
    ]
    if not sentences:
        return "Please enter your study notes first."

    result = "### Quiz\n\n"
    for i, sentence in enumerate(sentences[:10], 1):
        result += f"{i}. Which statement is directly related to the study material?\n\n"
        result += f"A. {sentence}\n"
        result += "B. This topic is unrelated to the material.\n"
        result += "C. This statement gives unrelated information.\n"
        result += "D. None of the above.\n"
        result += f"Answer: A\n\n"
    return result


@app.route("/ai-summarizer", methods=["GET", "POST"])
def ai_summarizer():

    if "user_id" not in session:
        return redirect(url_for("login"))

    summary = ""
    entered_text = ""

    if request.method == "POST":

        entered_text = request.form.get(
            "text",
            ""
        ).strip()

        if not entered_text:

            summary = "Please enter your study notes first."

        else:
            summary = local_summarize(entered_text)

    return render_template(
        "ai_summarizer.html",
        summary=summary,
        entered_text=entered_text
    )


@app.route("/question-generator", methods=["GET", "POST"])
def question_generator():

    if "user_id" not in session:
        return redirect(url_for("login"))

    questions = ""
    entered_text = ""

    if request.method == "POST":

        entered_text = request.form.get(
            "text",
            ""
        ).strip()

        if not entered_text:

            questions = "Please enter your study notes first."

        else:
            questions = local_questions(entered_text)

    return render_template(
        "question_generator.html",
        questions=questions,
        entered_text=entered_text
    )


@app.route("/quiz-generator", methods=["GET", "POST"])
def quiz_generator():

    if "user_id" not in session:
        return redirect(url_for("login"))

    quiz = ""
    entered_text = ""

    if request.method == "POST":

        entered_text = request.form.get(
            "text",
            ""
        ).strip()

        if not entered_text:

            quiz = "Please enter your study notes first."

        else:
            quiz = local_quiz(entered_text)

    return render_template(
        "quiz_generator.html",
        quiz=quiz,
        entered_text=entered_text
    )


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)