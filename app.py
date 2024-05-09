from flask import Flask, render_template, request, redirect, url_for,flash
from flask_mysqldb import MySQL
from flask import session
import secrets
import bcrypt
from datetime import datetime

app = Flask(__name__)
#app configuration
app.config['MYSQL_HOST'] = "localhost"
app.config['MYSQL_USER'] = "root"
app.config['MYSQL_DB'] = "task_master"
mysql = MySQL(app)
# Set your secret key
secret_key = secrets.token_hex(16)
app.secret_key = secret_key

@app.route('/')
def index():
    if 'user' in session:
        user_id=session['user']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = %s",(user_id,))
        user = cur.fetchone()
        today = datetime.now().date()
        todaytime = datetime.now()
        cur.execute("SELECT * FROM task WHERE DATE(due_date)=%s AND user_id = %s AND group_id IS NULL ORDER BY due_date ASC",(today,user_id))
        tasks = cur.fetchall()
        cur.execute("SELECT COUNT(*) FROM task WHERE DATE(due_date) < %s AND user_id = %s AND group_id IS NULL AND status != %s", (today, user_id, 'Completed'))
        overduecheck = cur.fetchone()[0]
        cur.close()

        return render_template('index.html',overduecheck=overduecheck,active_page='dash',useremail=user[2],username=user[1], tasks=tasks, today=todaytime)
    else:
        return redirect(url_for('sign_in'))


@app.route('/overdue')
def overdue():
    if 'user' in session:
        user_id=session['user']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = %s",(user_id,))
        user = cur.fetchone()
        today = datetime.now().date()
        todaytime = datetime.now()
        cur.execute("SELECT * FROM task WHERE DATE(due_date)<%s AND user_id = %s AND group_id IS NULL AND status != %s ORDER BY due_date ASC",(today,user_id, 'Completed'))
        tasks = cur.fetchall()
        cur.close()

        return render_template('overdue.html',active_page='overdue',useremail=user[2],username=user[1], tasks=tasks, today=todaytime)
    else:
        return redirect(url_for('sign_in'))



@app.route('/upcoming')
def upcoming():
    if 'user' in session:
        user_id=session['user']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = %s",(user_id,))
        user = cur.fetchone() 
        today = datetime.now().date()
        todaytime = datetime.now()
        cur.execute("SELECT * FROM task WHERE DATE(due_date)>%s AND user_id = %s AND group_id IS NULL ORDER BY due_date ASC",(today,user_id))
        tasks = cur.fetchall()
        cur.execute("SELECT COUNT(*) FROM task WHERE DATE(due_date) < %s AND user_id = %s AND group_id IS NULL AND status != %s", (today, user_id, 'Completed'))
        overduecheck = cur.fetchone()[0]
        cur.close()

        return render_template('upcoming.html',overduecheck=overduecheck,active_page='upcoming',useremail=user[2],username=user[1], tasks=tasks,today=todaytime)
    else:
        return redirect(url_for('sign_in'))

@app.route('/team', methods=['GET', 'POST'])
def team():
    if 'user' in session:
        user_id = session['user']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cur.fetchone()

        if request.method == 'POST':
            title = request.form['taskTitle']
            priority = request.form['taskPriority']
            description = request.form['description']
            dueDate = request.form['dueDate']
            user_id = session.get('user')  # Retrieve user ID from session

                # Perform basic validation
            if not all([title, priority, dueDate]):
                error="Fill all Input"

                # Insert data into the database
            cur = mysql.connection.cursor()
            cur.execute("SELECT MAX(task_id) FROM task")
            last_task_id = cur.fetchone()[0] + 1
            group_id = int(str(last_task_id) + str(user_id))
            cur.execute("INSERT INTO task (title, priority, description, due_date, user_id, group_id) VALUES (%s, %s, %s, %s, %s, %s)", 
                    (title, priority, description, dueDate, user_id, group_id))
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('team'))

        today = datetime.now().date()
        todaytime = datetime.now()
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cur.fetchone()
        cur.execute("SELECT * FROM task WHERE user_id = %s AND group_id IS NOT NULL", (user_id,))
        mytasks = cur.fetchall()
        cur.execute("""
            SELECT task.*, users.username
            FROM task
            INNER JOIN user_groups ON task.group_id = user_groups.group_id
            INNER JOIN users ON user_groups.user_id = users.user_id
            WHERE user_groups.user_id = %s
            """, (user_id,))
        othertasks = cur.fetchall()
        cur.execute("SELECT COUNT(*) FROM task WHERE DATE(due_date) < %s AND user_id = %s AND group_id IS NULL AND status != %s", (today, user_id, 'Completed'))
        overduecheck = cur.fetchone()[0]
        cur.close()

        task_id = request.args.get('id')

        return render_template('team.html',overduecheck=overduecheck,active_page='team',today=todaytime, useremail=user[2], username=user[1], mytasks=mytasks,othertasks=othertasks, task_id=task_id)
    else:
        return redirect(url_for('sign_in'))
  
@app.route('/task-detail/<task>')
def task_detail(task):
    if 'user' in session:
        user_id = session['user']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cur.fetchone()
        cur.execute("""
            SELECT task.*, users.username
            FROM task
            LEFT JOIN user_groups ON task.group_id = user_groups.group_id
            LEFT JOIN users ON user_groups.user_id = users.user_id
            WHERE task.task_id = %s """, (task,))
        task = cur.fetchone()
        cur.close()
        if task:
            return render_template('task-details.html', task=task)
        else:
            flash('Task not found', 'error')
            return redirect(url_for('team'))  # Redirect to dashboard or any other appropriate page
    else:
        flash('Please log in to view task details', 'error')
        return redirect(url_for('sign_in'))  # Redirect to login page



@app.route('/sign-in', methods=['GET','POST'])
def sign_in():
    if 'user' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):
            session['user'] = user[0] 
            return redirect(url_for('index'))
        else:
            return render_template('sign-in.html',email=email, error='Invalid email or password!')
    return render_template('sign-in.html')


@app.route('/sign-up')
def sign_up():
    return render_template('sign-up.html')

@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        username = request.form['user_name']
        email = request.form['email']
        password = request.form['password']
        cpassword = request.form['cpassword']
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_email = cur.fetchone()

        if existing_email:
            return render_template('sign-up.html', name=username, email=email, error='Email already in use!!')
        
        if password != cpassword:
            return render_template('sign-up.html', name=username, email=email, error='Passwords do not match!')
        
        cur.execute("INSERT INTO users(username, email, password) VALUES (%s, %s, %s)", (username, email, hashed_password))
        mysql.connection.commit()
        cur.close()
        
        return redirect(url_for('sign_in'))
    
@app.route('/add-task', methods=['POST'])
def add_task():
    if request.method == 'POST':
        title = request.form['taskTitle']
        priority = request.form['taskPriority']
        description = request.form['description']
        dueDate = request.form['dueDate']
        user_id = session.get('user')  # Retrieve user ID from session

        # Perform basic validation
        if not all([title, priority, dueDate]):
            error="Fill all Input"

        # Insert data into the database
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO task (title, priority, description, due_date, user_id) VALUES (%s, %s, %s, %s, %s)", 
                    (title, priority, description, dueDate, user_id))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('index'))


@app.route('/update-task/<back>', methods=['POST'])
def update_task(back):
    if request.method == 'POST':
        flash("Task Updated")
        id_data = request.form['id']
        title = request.form['taskTitle']
        priority = request.form['taskPriority']
        description = request.form['description']
        dueDate = request.form['dueDate']
        # Perform basic validation
        if not all([title, priority, dueDate]):
            error="Fill all Input"

        # Insert data into the database
        cur = mysql.connection.cursor()
        cur.execute("""
                    UPDATE task 
                    SET title=%s, priority=%s, description=%s, due_date=%s
                    WHERE task_id=%s
                    """, (title, priority, description, dueDate, id_data))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for(back))

    
@app.route('/addmember', methods=['POST'])
def addmember():
    if 'user' in session:
        user_id = session['user']
        cur = mysql.connection.cursor()
        if request.method == 'POST':
            group_id = request.form['id']
            email = request.form['email']
            
            # Check if the email exists in the database
            cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            member_id = cur.fetchone()
            if not member_id:
                flash("This email does not exist.")
                return redirect(url_for('team'))
            
            # Check if the user is trying to add themselves
            if member_id[0] == user_id:
                flash("You cannot add yourself to the task.")
                return redirect(url_for('team'))
            
            # Check if the member is already in the group
            cur.execute("SELECT user_id FROM user_groups WHERE user_id = %s AND group_id = %s", (member_id[0], group_id))
            already_in = cur.fetchone()
            if already_in:
                flash("Member already added.")
                return redirect(url_for('team'))
            
            # Insert the member into the group
            cur.execute("INSERT INTO user_groups (user_id, group_id) VALUES (%s, %s)", (member_id[0], group_id))
            mysql.connection.commit()
            flash("Member added successfully.")
            return redirect(url_for('team'))
    else:
        return redirect(url_for('sign_in'))

@app.route('/delete/<id_data>/<back>', methods=['POST','GET'])
def delete(id_data,back):
    flash("Task Deleted")
    cur= mysql.connection.cursor()
    cur.execute("DELETE FROM task WHERE task_id = %s", (id_data,))
    mysql.connection.commit()
    return redirect(url_for(back))

@app.route('/complete/<id_data>/<back>', methods=['POST','GET'])
def complete(id_data,back):
    flash("Task Completed")
    cur= mysql.connection.cursor()
    cur.execute("""
                UPDATE task 
                SET status = %s WHERE task_id = %s
                """, ('Completed',id_data))
    mysql.connection.commit()
    return redirect(url_for(back))

@app.route('/remove/<id_data>/<back>', methods=['POST','GET'])
def remove(id_data,back):
    if 'user' in session:
        user_id = session['user']
        flash("You Left in Team Task")
        cur= mysql.connection.cursor()
        cur.execute("DELETE FROM user_groups WHERE user_id = %s AND group_id = %s", (user_id,id_data))
        mysql.connection.commit()
        return redirect(url_for(back))

    
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
