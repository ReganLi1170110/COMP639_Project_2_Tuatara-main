from flask import render_template

from app import flask_app as app

from flask import render_template, request, redirect, url_for, flash, session
from app.repository import catch_repository, common_repository
import functools
from datetime import datetime

from app import flask_app, db
import app.utils as utils

def is_operator_assigned_to_line(operator_id, line_id):
    with db.get_cursor() as cur:
        cur.execute("SELECT 1 FROM User_Line WHERE user_id = %s AND line_id = %s", (operator_id, line_id))
        return cur.fetchone() is not None

# ----- US11: View operator assignments -----
@flask_app.route('/user_line')
@utils.login_required()
@utils.roles_required('Operator', 'Coordinator')
def user_line():
    with db.get_cursor() as cur:
        cur.execute("""
            SELECT l.line_id, l.name,
                   COALESCE(
                       (SELECT json_agg(json_build_object(
                           'user_id', u.user_id,
                           'first_name', u.first_name,
                           'last_name', u.last_name,
                           'email', u.email,
                           'phone_number', u.phone_number
                       ))
                        FROM User_Line ul
                        JOIN Users u ON ul.user_id = u.user_id
                        WHERE ul.line_id = l.line_id
                       ), '[]'::json) AS operators
            FROM Line l
            WHERE l.line_status = 'Active'
            ORDER BY l.name
        """)
        lines = cur.fetchall()
    return render_template('user_line.html', lines=lines,
                           current_user_id=session.get('user_id'),
                           current_role=session.get('role'))

# ----- US12: Admin manage operator assignments -----
@flask_app.route('/admin/operator/<int:user_id>')
@utils.login_required()
@utils.roles_required('Coordinator')
def admin_operator_detail(user_id):
    with db.get_cursor() as cur:
        cur.execute("""
            SELECT user_id, username, first_name, last_name, email, phone_number
            FROM Users WHERE user_id = %s AND role = 'Operator'
        """, (user_id,))
        operator = cur.fetchone()
        if not operator:
            flash('Operator not found.', 'danger')
            return redirect(url_for('users'))   # adjust if your user list endpoint differs

        cur.execute("""
            SELECT l.line_id, l.name,
                   CASE WHEN ul.user_id IS NOT NULL THEN true ELSE false END AS assigned
            FROM Line l
            LEFT JOIN User_Line ul ON l.line_id = ul.line_id AND ul.user_id = %s
            WHERE l.line_status = 'Active'
            ORDER BY l.name
        """, (user_id,))
        lines = cur.fetchall()
    return render_template('admin_operator_detail.html', operator=operator, lines=lines)

@flask_app.route('/admin/assign_line', methods=['POST'])
@utils.login_required()
@utils.roles_required('Coordinator')
def assign_line():
    operator_id = request.form.get('operator_id', type=int)
    line_id = request.form.get('line_id', type=int)
    action = request.form.get('action')
    if not operator_id or not line_id or action not in ['add', 'remove']:
        flash('Invalid request.', 'danger')
        return redirect(request.referrer or url_for('home'))

    with db.get_cursor() as cur:
        if action == 'add':
            cur.execute("SELECT 1 FROM User_Line WHERE user_id = %s AND line_id = %s", (operator_id, line_id))
            if not cur.fetchone():
                cur.execute("INSERT INTO User_Line (user_id, line_id) VALUES (%s, %s)", (operator_id, line_id))
                db.get_db().commit()
                flash('Line assigned successfully.', 'success')
            else:
                flash('Already assigned.', 'info')
        else:
            cur.execute("DELETE FROM User_Line WHERE user_id = %s AND line_id = %s", (operator_id, line_id))
            db.get_db().commit()
            flash('Assignment removed.', 'success')
    return redirect(url_for('admin_operator_detail', user_id=operator_id))



