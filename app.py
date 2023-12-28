import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, jsonify, request, session
from flask_session import Session
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash




from helpers import apology, login_required, lookup

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


if __name__ == "__main__":
    app.run(debug=True)


# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///project.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        # Verifique se a solicitação POST veio de um folder específico
        folder_name_clicked = request.form.get("folder_name_clicked")
        if folder_name_clicked:
            # Atualize o "last_seen" apenas para o folder clicado
            current_time = datetime.now()
            db.execute(
                "UPDATE flashcards SET last_seen = ? WHERE user_id = ? AND folder_name = ?",
                current_time, session["user_id"], folder_name_clicked
            )

    ''' FLASHCARDS FOLDERS '''
    folders = db.execute("""
        SELECT DISTINCT folder_name, folder_description, last_seen
        FROM flashcards
        WHERE user_id = ?
        """, session["user_id"])

    # Calcula o "Last Seen" para cada folder
    current_time = datetime.now()
    for folder in folders:
        last_seen_time = folder["last_seen"]
        if last_seen_time is not None:
            last_seen_time = datetime.fromisoformat(last_seen_time)
            time_difference = current_time - last_seen_time
            folder["last_seen"] = format_last_seen(time_difference)

    return render_template("index.html", folders=folders)



def format_last_seen(time_difference):
    if time_difference.total_seconds() < 60:
        return "just now"
    elif time_difference.total_seconds() < 3600:
        minutes = int(time_difference.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif time_difference.total_seconds() < 86400:
        hours = int(time_difference.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif time_difference.days < 30:
        days = time_difference.days
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif time_difference.days < 365:
        months = time_difference.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = time_difference.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"




@app.route("/edit_folder/<folder_name>", methods=["GET", "POST"])
@login_required
def edit_folder(folder_name):
    if request.method == "GET":
        folder = db.execute(
            "SELECT * FROM flashcards WHERE user_id = ? AND folder_name = ?",
            session["user_id"], folder_name
        )
        return render_template("edit_flashcards.html", folder=folder[0])

    if request.method == "POST":
        new_name = request.form.get("new_name")
        new_description = request.form.get("new_description")

        # Atualize os valores no banco de dados
        db.execute(
            "UPDATE flashcards SET folder_name = ?, folder_description = ? WHERE folder_name = ? AND user_id = ?",
            new_name, new_description, folder_name, session["user_id"]
        )

        # Atualize a coluna "last_seen" no banco de dados com o tempo atual
        current_time = datetime.now()
        db.execute(
            "UPDATE flashcards SET last_seen = ? WHERE folder_name = ? AND user_id = ?",
            current_time, new_name, session["user_id"]
        )

        # Redirecione para a página inicial ou outra página apropriada
        return redirect("/")


@app.route("/delete_folder/<folder_name>", methods=["POST"])
@login_required
def delete_folder(folder_name):
    if request.method == "POST":
        # Lógica para excluir a pasta com base no folder_name
        db.execute(
            "DELETE FROM flashcards WHERE folder_name = ? AND user_id = ?",
            folder_name, session["user_id"]
        )
        return redirect("/")






@app.route("/edit_flashcards/<folder_name>", methods=["GET", "POST"])
@login_required
def edit_flashcards_by_folder(folder_name):
    if request.method == "GET":
        flashcards = db.execute(
            "SELECT * FROM flashcards WHERE user_id = ? AND folder_name = ?",
            session["user_id"], folder_name
        )
        return render_template("edit_flashcards.html", flashcards=flashcards, folder_name=folder_name)

    if request.method == "POST":
        flashcard_ids = request.form.getlist("flashcard_id")  # Altere para "flashcard_id"
        new_front_values = request.form.getlist("new_front")
        new_back_values = request.form.getlist("new_back")

        # Loop through the submitted data and update flashcards
        for flashcard_id, new_front, new_back in zip(flashcard_ids, new_front_values, new_back_values):
            db.execute(
                "UPDATE flashcards SET flashcard_front = ?, flashcard_back = ? WHERE id = ? AND user_id = ?",
                new_front, new_back, flashcard_id, session["user_id"]
            )

        return redirect(f"/edit_flashcards/{folder_name}")


@app.route("/delete_flashcard", methods=["POST"])
@login_required
def delete_flashcard():
    if request.method == "POST":
        folder_id = request.form.get("folder_id")
        folder_name = request.form.get("folder_name")
        db.execute(
            "DELETE FROM flashcards WHERE folder_id = ? AND user_id = ?",
            folder_id, session["user_id"]
        )

        # Redirecione para a página de edição de flashcards com o nome da pasta
        return redirect(f"/flashcards/{folder_name}")


@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        folder_name = request.form.get("folder_name")
        folder_description = request.form.get("folder_description")

        flashcards = []  # Inicialize uma lista vazia para armazenar os flashcards

        flashcard_front = request.form.get("flashcard_front")
        flashcard_back = request.form.get("flashcard_back")
        if flashcard_front and flashcard_back:
            flashcards.append({
                "flashcard_front": flashcard_front,
                "flashcard_back": flashcard_back
            })

            # Inserir o flashcard na tabela flashcards
            db.execute(
                "INSERT INTO flashcards (user_id, folder_name, folder_description, flashcard_front, flashcard_back, difficulty_level) VALUES (?, ?, ?, ?, ?, ?)",
                session["user_id"], folder_name, folder_description, flashcard_front, flashcard_back
            )

        # Process additional flashcards
        flashcard_count = int(request.form.get("flashcard_count"))
        for i in range(1, flashcard_count + 1):
            flashcard_front = request.form.get(f"flashcard_front_{i}")
            flashcard_back = request.form.get(f"flashcard_back_{i}")

            if flashcard_front and flashcard_back:
                flashcards.append({
                    "flashcard_front": flashcard_front,
                    "flashcard_back": flashcard_back
                })

                # Inserir o flashcard na tabela flashcards
                db.execute(
                    "INSERT INTO flashcards (user_id, folder_name, folder_description, flashcard_front, flashcard_back) VALUES (?, ?, ?, ?, ?)",
                    session["user_id"], folder_name, folder_description, flashcard_front, flashcard_back
                )

        return render_template("flashcards.html", folder_name=folder_name, success=True, flashcards=flashcards)

    return render_template("create.html", success=False)


@app.route("/flashcards/<folder_name>", methods=["GET", "POST"])
@login_required
def flashcards_by_folder(folder_name):
    if request.method == "POST":
        new_front = request.form.get("new_front")
        new_back = request.form.get("new_back")
        flashcard_id = request.form.get("flashcard_id")

        # Atualize as informações do flashcard no banco de dados
        db.execute(
            "UPDATE flashcards SET flashcard_front = ?, flashcard_back = ? WHERE folder_id = ? AND user_id = ?",
            new_front, new_back, flashcard_id, session["user_id"]
        )

        # Busque os flashcards atualizados no banco de dados
        updated_flashcards = db.execute(
            "SELECT * FROM flashcards WHERE user_id = ? AND folder_name = ?",
            session["user_id"], folder_name
        )

        # Redirecione ou retorne uma resposta adequada após a atualização
        return render_template("flashcards.html", flashcards=updated_flashcards)

    if request.method == "GET":
        # Atualize o "last_seen" apenas para a pasta especificada
        current_time = datetime.now()
        db.execute(
            "UPDATE flashcards SET last_seen = ? WHERE user_id = ? AND folder_name = ?",
            current_time, session["user_id"], folder_name
        )

    # Se o método for GET, busque flashcards na pasta específica
    flashcards_in_folder = db.execute(
        "SELECT * FROM flashcards WHERE user_id = ? AND folder_name = ?",
        session["user_id"], folder_name
    )

    return render_template("flashcards.html", flashcards=flashcards_in_folder)

@app.route("/review", methods=["GET"])
@login_required
def display_review():
    return render_template("review.html")


@app.route("/difficulty", methods=["GET", "POST"])
@login_required
def display_difficulty():
    data = request.json
    if request.method == "POST":
        data = request.json  # Obtenha os dados JSON do POST

        difficulty_level = data.get("difficulty")
        folder_id = data.get("folder_id")

        print(f"Received difficulty: {difficulty_level}")
        print(f"Received folder_id: {folder_id}")

        if difficulty_level in ["easy", "medium", "hard"]:
            try:
                # Atualize o nível de dificuldade do flashcard específico no banco de dados
                db.execute(
                    "UPDATE flashcards SET difficulty_level = ? WHERE folder_id = ? AND user_id = ?",
                    difficulty_level, folder_id, session["user_id"]
                )

                # Commit changes to the database
                db.commit()
                print("Flashcard difficulty updated successfully!")
                return jsonify({'success': True})

            except Exception as e:
                # Se houver algum erro na execução do SQL, retorne um erro
                print(f"Erro ao executar a query SQL: {str(e)}")
                return jsonify({'success': False, 'error': str(e)})

    # Retorna uma resposta padrão se o método não for POST ou houver algum problema
    return jsonify({'success': False, 'error': 'Invalid request'})




@app.route("/easy_folder")
@login_required
def easy_folder():
    # Se o método for GET, busque flashcards na pasta específica
    flashcards_in_folder = db.execute(
        "SELECT * FROM flashcards WHERE user_id = ? AND difficulty_level = ?",
        session["user_id"], "easy"
    )

    # Busca os flashcards fáceis do banco de dados para o usuário logado
    flashcards = db.execute("SELECT * FROM flashcards WHERE user_id = ? AND difficulty_level = ?", session["user_id"], "easy")
    return render_template("easy_folder.html", flashcards=flashcards)

@app.route("/medium_folder")
@login_required
def medium_folder():
     # Se o método for GET, busque flashcards na pasta específica
    flashcards_in_folder = db.execute(
        "SELECT * FROM flashcards WHERE user_id = ? AND difficulty_level = ?",
        session["user_id"], "medium"
    )

    # Busca os flashcards fáceis do banco de dados para o usuário logado
    flashcards = db.execute("SELECT * FROM flashcards WHERE user_id = ? AND difficulty_level = ?", session["user_id"], "medium")
    return render_template("medium_folder.html", flashcards=flashcards)

@app.route("/hard_folder")
@login_required
def hard_folder():
    # Se o método for GET, busque flashcards na pasta específica
    flashcards_in_folder = db.execute(
        "SELECT * FROM flashcards WHERE user_id = ? AND difficulty_level = ?",
        session["user_id"], "hard"
    )

    # Busca os flashcards fáceis do banco de dados para o usuário logado
    flashcards = db.execute("SELECT * FROM flashcards WHERE user_id = ? AND difficulty_level = ?", session["user_id"], "hard")
    return render_template("hard_folder.html", flashcards=flashcards)


@app.route("/login", methods=["GET", "POST"])
def login():
    """LOG USER IN """

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("must provide password")

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        print("Number of rows:", len(rows))
        print("Rows:", rows)

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
                flash("Invalid username and/or password")

        else:
            # Remember which user has logged in
            session["user_id"] = rows[0]["id"]
            # After setting session["user_id"]
            print("Logged in user:", session["user_id"])

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """LOG USER OUT """

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """REGISTER USER """
    if request.method == "GET":
        return render_template("register.html")

    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            flash("Please enter your username")

        if not password:
            flash("Please enter your password")

        if not confirmation:
            flash("Please enter your confirmation password")

        if password != confirmation:
            flash("Passwords do not match")

        hash = generate_password_hash(password)

    try:
        db.execute('INSERT INTO users (username, hash) VALUES (?, ?)', username, hash)
    except:
        flash("Username already exists")

    # Log user in if registration is successful
    rows = db.execute("SELECT * FROM users WHERE username = ?", username)

    if len(rows) == 1:
        session["user_id"] = rows[0]["id"]
        # Redirect user to home page
        return redirect("/")


@app.route("/confetti")
@login_required
def show_confetti():
    """MESSAGE WHEN USER FINISH FLASHCARD """
    return render_template("confetti.html")

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """USER PROFILE"""
    if request.method == "POST":
        username = request.form.get("username_profile")
        current_password = request.form.get("current_password")
        new_password = request.form.get("password_profile")
        new_password_again = request.form.get("new_password_again")


        # Ensure all fields are provided
        if not username or not current_password or not new_password or not new_password_again:
            flash("All fields are required.", "danger")
            return redirect("/profile")

        # Query database for user
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)

        # Check if username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], current_password):
            flash("Invalid username and/or password.", "danger")
            return redirect("/profile")

        # Check if new password matches
        if new_password != new_password_again:
            flash("Passwords don't match. Try again!", "danger")
            return redirect("/profile")

        # Update user's password
        db.execute("UPDATE users SET hash = :hash WHERE id = :id",
            hash=generate_password_hash(new_password), id=session["user_id"])


        flash("Congratulations! Password has been changed!", "success")

        return redirect("/")
    else:
        return render_template("profile.html")
