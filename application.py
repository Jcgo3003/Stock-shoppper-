import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    if request.method == "GET":
        # Getting data from history now
        usu = session["user_id"]
        con = db.execute("SELECT symbol, name, SUM(shares) FROM history_now WHERE id_user = :usu GROUP BY Symbol HAVING SUM(shares) > 0", usu=usu)

        # Reading and getting prices for each symbol
        price = []
        for cosas in con:
            # Adding prices to price_total
            price_each = lookup(cosas['symbol'])
            price.append(price_each['price'])

        # Getting users cash
        cash = db.execute("SELECT cash FROM users WHERE id= :usu", usu=usu)

    return render_template("index.html", con=con, price=price, cash=cash[0]['cash'])
    # return apology("TODO")

@app.route("/cha_pass", methods=["GET", "POST"])
@login_required
def change_pass():
    """Changing user password """
    if request.method == "POST":
        # Ensure that the user writes a password
        if not request.form.get("pass"):
            return apology("Must provide a password")

        # Ensure that the user doble-writes a password
        if not request.form.get("d_pass"):
            return apology("Must re-type the password")

        # Ensure that the user typed Old password
        if not request.form.get("old"):
            return apology("Must type old password")

        # Getting the user id
        id_usu = session.get("user_id")

        # Getting the old password
        check = db.execute("SELECT hash FROM users WHERE id= :id_usu", id_usu=id_usu)
        print("Hash es",check[0]['hash'])

        if len(check) != 1 or not check_password_hash(check[0]['hash'], request.form.get("old")):
            return apology("Old password does not match")

        # Checking the passwords match
        password = str(request.form.get("pass"))
        re_pass  = str(request.form.get("d_pass"))
        print("compa", password, re_pass)

        if password != re_pass:
            return apology("Passwords does not match")

        # Until here everything must be all right
        # Hashing the password
        password = generate_password_hash(re_pass)

        # Updting the password for the users
        change = db.execute("UPDATE users SET hash= :password WHERE id= :id_usu", password=password, id_usu=id_usu)

        # Ensure that all went well
        if change == None:
            return apology("There was a problem updating your password")

        # Login out the user
        session.clear()

        return render_template("changed.html")
    # Showing the template for submit the information4
    else:
        return render_template("change.html")

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # Getting the post request
    if request.method == "POST":
        # Making sure that there is no black spaces in symbol and shares space
        if not request.form.get("compania"):
            return apology("Must provide a company symbol")
        if not request.form.get("numero"):
            return apology("Must provide a quantity")

        # Checking the symbol via lookup - the number in share doesn't need to be cheaked since i
        # Cheked already via html
        api_check = lookup(request.form.get("compania"))

        if api_check == None:
            return apology("Please check company symbol")

        # Cheking the user's cash
        nom_usu = session.get('user_id')

        # checking enought money
        checkar = db.execute("SELECT * FROM users where id = :nom_usu", nom_usu=nom_usu)
        dinero = checkar[0]['cash']

        # Number of shares
        num_shares = int(request.form.get("numero"))
        costo = api_check["price"] * num_shares

        if dinero < costo:
            return apology("Can't afford")
        # Buying the stuck - writing into "history-now" table
        else:
            simbolo = api_check["symbol"]
            nom_c = api_check["name"]
            precio_com = api_check["price"]

            now = datetime.datetime.now()
            fecha = now.strftime("%Y-%m-%d %H:%M:%S")

            id_usu = session["user_id"]

            # Buying the stuck
            insertion = db.execute ("""INSERT INTO "history_now" ("id_trans","symbol","name","shares","price_buy","date","id_user")
                                    VALUES (NULL, :simbolo, :nom_c, :num_shares, :precio_com, :fecha, :id_usu)""",
                                    simbolo = simbolo, nom_c = nom_c, num_shares = num_shares, precio_com = precio_com, fecha = fecha, id_usu = id_usu )

            # Paying the stuck
            total = dinero - (num_shares * precio_com)
            updating = db.execute ("""UPDATE 'users' SET cash = :total WHERE id= :id_usu""",  total=total, id_usu=id_usu )

        if (insertion == None) or (updating == None):
            return apology("Error while buying")
        else:
            # render success template for buy
            act='bought'
            return render_template("success.html", act=act, num_shares=num_shares, simbolo=simbolo, precio_com=precio_com, costo=costo )
        # Actually buying the share
        # Debo crear una tabla aparte donde esten los usuarios y sus
        # compras, esa tabla debe tener cuando se compro y cuantos y esa informacion se
        # debe juntar con la tabla usuarios para desplegar una informacion final
        # actualizar = # crear una tabla donde esten todos las compras de los usuarios

    # Rendering buy form
    else:
        return render_template("buy.html")


@app.route("/history", methods=["GET"])
@login_required
def history():
    """Show history of transactions"""
    # If the user visits the page
    if request.method == 'GET':

        # Getting the user id
        id_usu = session.get("user_id")

        # Getting data from the DB - id_transation, symbol, Name, shares, price, date.
        tabla = db.execute("SELECT id_trans, symbol, name, shares, price_buy, date FROM history_now WHERE id_user = :id_usu ORDER BY id_trans", id_usu=id_usu)

        # Inserting '$' to 'price_buy'
        for a in range (len(tabla)):
            x = tabla[a].get("price_buy")
            x = '$' + str(x)
            tabla[a]['price_buy'] = x

        return render_template("historia.html", tabla=tabla)

    # There is no else, this page would only show information, not getting info from the user



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        # Also remember the name of the user # !!!!!!!!!!!!
        # session["nom_usu"] = rows[0]["username"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # Render template quoting a price
    if request.method == "POST":
        # Ensure that a name was sumitted
        if not request.form.get("compania"):
            return apology("No name provided", 403)
        else:
            # calling lookup to get the quote
            api_check = lookup(request.form.get("compania"))
            if api_check == None:
                return apology("Invalid BMV Symbol", 403)

        return render_template("quoted.html", name = api_check['name'], sym = api_check['symbol'], precio = api_check["price"] )

    # Render template for firts time.
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # Terminando cualquier sesion de usuario abierta - forget any used_id
    session.clear()

    # Atrapando por method de una forma html.
    if request.method == "POST":
        # Checking each of the special caracteristics
        # 1 Must check if there are Blank spaces for users and passwords
        if not request.form.get("username"):
            return apology("None username writed", 403)

        if not request.form.get("pass"):
            return apology("No password has been set", 403)

        if not request.form.get("confirmation"):
            return apology("No password has been re-typed", 403)

        # 2 Cheking than the passwords match
        password = request.form.get("pass")
        confirmation = request.form.get("confirmation")

        if password != confirmation:
            return apology("Passwords does not match", 403)

        # Getting the data for the html and generating the hash
        pass_h = generate_password_hash(password)
        username = request.form.get("username")

        insertion = db.execute ("""INSERT INTO "users" ("id","username","hash") VALUES (NULL,:username,:pass_h)""",
                                username = username, pass_h = pass_h)

        # 3 Cheking if the name already exist
        if ( insertion == None ):
            return apology("Username already exist", 403)
        else:
            return render_template("registered.html")

    return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        # Getting the POST request
        # Ensure Symbol was sumited
        if not request.form.get("compania"):
            return apology("Must provide wity Symbol", 403)
        # Ensure shares was sumited
        if not request.form.get("numero"):
            return apology("Must provide with number of shares", 403)

        # Checking the cost of the share - Its important that api_check goes here so Ensure the user has shares to sell work
        api_check = lookup( request.form.get("compania") )

        if api_check == None:
            return apology("Please check company symbol", 404)

        # Ensure the user has shares to sell
        id_usu = session["user_id"]
        name_comp = api_check["symbol"]
        check_sha = db.execute("SELECT symbol, SUM(shares) FROM history_now WHERE id_user= :id_usu AND symbol= :name_comp GROUP BY symbol", id_usu=id_usu, name_comp=name_comp)

        # Getting the number of shares of the user and the number of shares that wants to sell
        shares_sell = int(request.form.get("numero"))

        if (check_sha == None):
            return apology("There was a problem reading your account information", 202)

        num_shares = int(check_sha[0]['SUM(shares)'])

        if (num_shares == 0):
            return apology("You have no shares of this company", 202)
        elif (num_shares < shares_sell):
            return apology("You have not enough shares to sell", 202 )

        # Inserting the new data Into the DB
        simbolo = api_check["symbol"]
        nom_c = api_check["name"]
        precio_vent = api_check["price"]

        share = shares_sell * - 1

        now = datetime.datetime.now()
        fecha = now.strftime("%Y-%m-%d %H:%M:%S")

        # all the data is now correct we query the DB
        sell = db.execute("""INSERT INTO "history_now" ("id_trans", "symbol", "name", "shares", "price_buy", "date", "id_user")
                            VALUES  (NULL, :simbolo, :nom_c, :share, :precio_vent, :fecha, :id_usu)""",
                            simbolo=simbolo, nom_c=nom_c, share=share, precio_vent=precio_vent, fecha=fecha, id_usu=id_usu )

        # Updating cash in the users index
        cash = db.execute("SELECT cash FROM users WHERE id= :id_usu", id_usu=id_usu )

        costo = shares_sell * precio_vent
        cash_final = round(cash[0]['cash'] + costo , 2)

        update = db.execute("UPDATE users SET cash= :cash_final WHERE id= :id_usu", cash_final=cash_final, id_usu=id_usu)

        if (sell == None) or (update == None):
            return apology("Error while buying", 202)
        else:
            act="Sold"
            return render_template("success.html", act=act, num_shares=shares_sell, simbolo=simbolo, precio_com=precio_vent, costo=costo)
    else:
        # Rendering the sell template
        return render_template("sell.html")


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

# Bugs
# Index despliega los shares incluso cuando ya hay 0 de esos shares
# Permite vender shares incluso cuando no los tienes >>>>>>> LISTO