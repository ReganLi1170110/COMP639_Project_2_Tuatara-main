import os
from werkzeug.utils import secure_filename
from flask import render_template, request, redirect, url_for, flash, session
from app import flask_app as app
import app.utils as utils
from app.repository import (
    core_repository,
    user_repository,
    group_settings_repository,
    donation_repository
)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'jpg', 'jpeg', 'png'}

@app.route('/account/donation-settings', methods=['GET', 'POST'])
@utils.login_required('Please log in to access donation settings.')
@utils.roles_required('Coordinator', 'Admin')
def account_donation_settings():
    current_user = user_repository.get_user_by_id(session.get('user_id'))
    if current_user is None:
        session.clear()
        flash('User not found. Please log in again.', 'danger')
        return redirect(url_for('login'))

    user_role = session.get('role')

    if user_role == 'Admin':
        if request.method == 'POST':
            footer_text = request.form.get('receipt_footer', '').strip()
            if len(footer_text) > 200:
                flash('Footer text exceeds the limit of 200 characters.', 'danger')
                return redirect(url_for('account_donation_settings'))

            logo_file = request.files.get('receipt_logo')
            logo_url = group_settings_repository.get_site_setting('receipt_logo', '')

            if logo_file and logo_file.filename:
                if not allowed_file(logo_file.filename):
                    flash('Only JPG and PNG images are allowed.', 'danger')
                else:
                    filename = secure_filename(logo_file.filename)
                    save_path = os.path.join(app.config['UPLOAD_FOLDER'], 'receipts', filename)
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    logo_file.save(save_path)
                    logo_url = url_for('static', filename=f'uploads/receipts/{filename}')

            try:
                group_settings_repository.set_site_setting('receipt_logo', logo_url)
                group_settings_repository.set_site_setting('receipt_footer', footer_text)
                flash('Global receipt settings updated.', 'success')
            except Exception:
                flash('Could not save receipt settings.', 'danger')
            return redirect(url_for('account_donation_settings'))

        # GET
        receipt_logo = group_settings_repository.get_site_setting('receipt_logo', '')
        receipt_footer = group_settings_repository.get_site_setting('receipt_footer', '')
        return render_template('account_donation_settings.html', is_sa=True, receipt_logo=receipt_logo, receipt_footer=receipt_footer)

    group_id = session.get('group_id')
    if not group_id:
        flash('No group selected. Choose a group first.', 'warning')
        return redirect(url_for('change_group'))

    group_info = core_repository.get_group_by_id(group_id)

    if request.method == 'POST':
        enabled = True if request.form.get('donation_enabled') == 'on' else False
        impact_description = request.form.get('impact_description', '').strip()
        try:
            group_settings_repository.set_group_setting(group_id, 'donation_enabled', enabled)
            group_settings_repository.set_group_setting(group_id, 'impact_description', impact_description)
            flash('Donation settings updated.', 'success')
        except Exception:
            flash('Could not save donation settings.', 'danger')
        return redirect(url_for('account_donation_settings'))

    # GET
    try:
        donation_enabled = group_settings_repository.get_group_setting(group_id, 'donation_enabled', True)
        impact_description = group_settings_repository.get_group_setting(group_id, 'impact_description', '')
    except Exception:
        donation_enabled = True
        impact_description = ''

    return render_template('account_donation_settings.html', is_sa=False, group_info=group_info, donation_enabled=donation_enabled, impact_description=impact_description)



@app.route('/donate', methods=['GET', 'POST'])
def donate():
    """Public donation page accessible to all users.

    GET: show donation form (optionally for a public group via `group_id`).
    POST: accept donation form submission and persist using donation_repository.
    """
    group = None
    group_id = request.values.get('group_id')
    if group_id:
        try:
            gid = int(group_id)
            g = core_repository.get_group_by_id(gid)
            if g and g.get('status') == 'Active':
                is_enabled = group_settings_repository.get_group_setting(gid, 'donation_enabled', True)
                if is_enabled:
                    group = g
        except Exception:
            group = None
    # Fetch all active groups for selection in the form
    try:
        public_groups = donation_repository.get_all_groups_for_donate()
        public_groups = [
            g for g in public_groups
            if group_settings_repository.get_group_setting(g['group_id'], 'donation_enabled', True)
        ]
    except Exception:
        public_groups = []

    # Fetch impact descriptions for public groups
    impact_descriptions = {}
    for g in public_groups:
        gid = g.get('group_id')
        if gid:
            try:
                desc = group_settings_repository.get_group_setting(gid, 'impact_description', '').strip()
                if desc:
                    impact_descriptions[str(gid)] = desc
            except Exception:
                pass

    initial_impact_description = impact_descriptions.get(str(group['group_id']), '') if (group and 'group_id' in group) else ''

    if request.method == 'POST':
        amount_raw = request.form.get('amount', '').strip()
        donation_type = request.form.get('donation_type', '').strip()
        donor_name = request.form.get('donor_name', '').strip()
        contact_email = request.form.get('contact_email', '').strip()
        message = request.form.get('message', '').strip() or None
        anonymous = request.form.get('anonymous') == 'on'

        errors = False

        # basic validation
        try:
            amount = float(amount_raw)
            if amount <= 0:
                flash('Donation amount must be greater than zero.', 'danger')
                errors = True
        except Exception:
            flash('Invalid donation amount.', 'danger')
            errors = True

        if donation_type not in ('group', 'platform', 'general'):
            flash('Invalid donation type selected.', 'danger')
            errors = True

        # If it's a group donation, ensure a valid active group_id was provided/selected
        if donation_type == 'group' and not group:
            flash('Please select a valid group for a Group donation.', 'danger')
            errors = True

        if contact_email and '@' not in contact_email:
            flash('Please enter a valid contact email address.', 'danger')
            errors = True

        if anonymous:
            donor_name = None

        if errors:
            return render_template('donate.html', group=group,
                                   public_groups=public_groups,
                                   impact_descriptions=impact_descriptions,
                                   initial_impact_description=initial_impact_description,
                                   amount=amount_raw, donation_type=donation_type,
                                   donor_name=donor_name, contact_email=contact_email,
                                   message=message, anonymous=anonymous)

        # persist donation (record donor_id if logged in)
        donation = {
            'amount': float(amount),
            'donation_type': donation_type.title(),
            'donor_name': donor_name,
            'contact_email': contact_email,
            'message': message,
            'anonymous': bool(anonymous),
            'group_id': int(group['group_id']) if group else None,
            # Only store donor_id when the donor is not anonymous
            'donor_id': (session.get('user_id') if session.get('user_id') and not anonymous else None),
        }
        try:
            created = donation_repository.create_donation(donation)
            if session.get('user_id') and not anonymous:
                try:
                    from app.repository import badge_repository
                    badge_repository.add_user_points(session.get('user_id'), badge_repository.BadgeAction.DONATION, 'Donation')
                except Exception:
                    pass
            flash('Thank you for your donation.', 'success')
            return redirect(url_for('donate'))
        except Exception as e:
            flash(f'Could not record donation: {e}', 'danger')
            return render_template('donate.html', group=group, public_groups=public_groups,
                                   impact_descriptions=impact_descriptions,
                                   initial_impact_description=initial_impact_description)

    return render_template('donate.html', group=group, public_groups=public_groups,
                           impact_descriptions=impact_descriptions,
                           initial_impact_description=initial_impact_description)


@app.route('/superadmin/donations', methods=['GET'])
@utils.login_required_without_group_checking()
@utils.roles_required('Admin')
def sa_donations():
    """Super Admin donation records management page showing all donation records across all groups."""
    donation_records = donation_repository.get_all_donations_with_group_names()
    total_amount = sum(d['amount'] for d in donation_records)
    return render_template('sa_donations.html', donation_records=donation_records, total_amount=total_amount)

