
import io, csv
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response, current_app
from . import db
from .models import Unit, Step, UnitStep, Audit

bp = Blueprint('main', __name__)

@bp.app_template_filter('dt')
def format_dt(value):
    if not value:
        return ''
    return value.strftime('%Y-%m-%d %H:%M:%S')

@bp.route('/')
def index():
    steps = Step.query.filter_by(active=True).order_by(Step.sequence).all()
    totals = {s.name: {'pending': 0, 'pass': 0, 'fail': 0} for s in steps}
    for s in steps:
        for r in UnitStep.query.filter_by(step_id=s.id).all():
            totals[s.name][r.status] += 1
    unit_count = Unit.query.count()
    return render_template('index.html', steps=steps, totals=totals, unit_count=unit_count)

@bp.route('/scan', methods=['GET', 'POST'])
def scan():
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if not code:
            flash('No code scanned', 'warning')
            return redirect(url_for('main.scan'))
        unit = Unit.query.filter_by(serial=code).first()
        if not unit:
            # Auto-create only if this station matches the FIRST step name
            station = (request.cookies.get('station') or '').strip()
            first_step = Step.query.filter_by(active=True).order_by(Step.sequence).first()
            allow_auto = current_app.config.get('AUTO_CREATE_FIRST_STATION', True)
            if allow_auto and first_step and station.lower() == first_step.name.lower():
                unit = Unit(serial=code)
                db.session.add(unit)
                db.session.flush()
                for s in Step.query.filter_by(active=True).order_by(Step.sequence).all():
                    db.session.add(UnitStep(unit_id=unit.id, step_id=s.id, status='pending'))
                db.session.commit()
                flash(f'Created new unit {code} at first station "{station}".', 'success')
                return redirect(url_for('main.unit_detail', serial=unit.serial))
            else:
                msg = f'Unit with serial {code} not found.'
                if first_step:
                    msg += f' Only the first station ("{first_step.name}") can create new units.'
                flash(msg, 'danger')
                return redirect(url_for('main.scan'))
        return redirect(url_for('main.unit_detail', serial=unit.serial))
    return render_template('scan.html')

@bp.route('/units/<serial>', methods=['GET', 'POST'])
def unit_detail(serial):
    unit = Unit.query.filter_by(serial=serial).first_or_404()
    steps = Step.query.filter_by(active=True).order_by(Step.sequence).all()
    ustates = {us.step_id: us for us in UnitStep.query.filter_by(unit_id=unit.id).all()}
    if request.method == 'POST':
        step_id = int(request.form['step_id'])
        new_status = request.form['status']
        operator = (request.form.get('operator', '') or request.cookies.get('operator') or '').strip() or None
        notes = request.form.get('notes', '').strip() or None
        station = request.cookies.get('station') or None
        us = ustates.get(step_id)
        if not us:
            us = UnitStep(unit_id=unit.id, step_id=step_id, status='pending')
            db.session.add(us)
            db.session.flush()
        old_status = us.status
        if old_status != new_status:
            us.status = new_status
            us.updated_at = datetime.utcnow()
            us.station = station
            us.operator = operator
            us.notes = notes
            db.session.add(Audit(
                unit_serial=unit.serial,
                step_name=Step.query.get(step_id).name,
                old_status=old_status,
                new_status=new_status,
                station=station,
                operator=operator,
                notes=notes
            ))
            db.session.commit()
            flash('Updated', 'success')
        else:
            flash('No change', 'info')
        return redirect(url_for('main.unit_detail', serial=unit.serial))
    return render_template('unit_detail.html', unit=unit, steps=steps, ustates=ustates)


@bp.route('/admin')
def admin():
    steps_active = Step.query.filter_by(active=True).order_by(Step.sequence).all()
    steps_inactive = Step.query.filter_by(active=False).order_by(Step.sequence).all()
    return render_template('admin.html', steps=steps_active, archived=steps_inactive)


@bp.route('/admin/steps', methods=['POST'])
def admin_steps():
    action = request.form.get('action')
    if action == 'add':
        name = request.form['name'].strip()
        if not name:
            flash('Step name required', 'warning')
            return redirect(url_for('main.admin'))
        max_seq = db.session.query(db.func.max(Step.sequence)).scalar() or 0
        db.session.add(Step(name=name, sequence=max_seq + 1))
        db.session.commit()
        # backfill UnitStep rows for existing units
        step = Step.query.filter_by(name=name).first()
        for u in Unit.query.all():
            db.session.add(UnitStep(unit_id=u.id, step_id=step.id, status='pending'))
        db.session.commit()
        flash('Step added', 'success')
    elif action == 'reseq':
        order = request.form.getlist('step_id[]')
        for i, sid in enumerate(order, start=1):
            s = Step.query.get(int(sid))
            s.sequence = i
            db.session.add(s)
        db.session.commit()
        flash('Reordered', 'success')
    return redirect(url_for('main.admin'))

@bp.route('/admin/import', methods=['POST'])
def admin_import():
    f = request.files.get('csv')
    if not f:
        flash('Upload a CSV with header "serial"', 'warning')
        return redirect(url_for('main.admin'))
    text = f.read().decode('utf-8', errors='ignore')
    reader = csv.DictReader(io.StringIO(text))
    added = 0
    for row in reader:
        serial = (row.get('serial') or '').strip()
        if not serial:
            continue
        if not Unit.query.filter_by(serial=serial).first():
            u = Unit(serial=serial)
            db.session.add(u)
            db.session.flush()
            for s in Step.query.filter_by(active=True).order_by(Step.sequence).all():
                db.session.add(UnitStep(unit_id=u.id, step_id=s.id, status='pending'))
            added += 1
    db.session.commit()
    flash(f'Imported {added} units', 'success')
    return redirect(url_for('main.admin'))

@bp.route('/admin/export')
def admin_export():
    si = io.StringIO()
    w = csv.writer(si)
    steps = Step.query.filter_by(active=True).order_by(Step.sequence).all()
    # Header: serial, then for each step: "<Step> Status", "<Step> Notes"
    header = ['serial']
    for s in steps:
        header.append(f"{s.name} Status")
        header.append(f"{s.name} Notes")
    w.writerow(header)
    for u in Unit.query.order_by(Unit.serial).all():
        row = [u.serial]
        ustates = {us.step_id: us for us in UnitStep.query.filter_by(unit_id=u.id).all()}
        for s in steps:
            us = ustates.get(s.id)
            status = us.status if us else 'pending'
            notes = (us.notes or '') if us else ''
            row.extend([status, notes])
        w.writerow(row)
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=status_export.csv"
    output.headers["Content-type"] = "text/csv"
    return output


@bp.route('/set-station', methods=['POST'])
def set_station():
    resp = make_response(redirect(request.referrer or url_for('main.index')))
    station = (request.form.get('station') or '').strip()
    resp.set_cookie('station', station, max_age=60*60*24*365)
    return resp


@bp.route('/admin/steps/delete', methods=['POST'])
def admin_delete_step():
    sid = int(request.form['step_id'])
    s = Step.query.get_or_404(sid)
    s.active = False
    db.session.add(s); db.session.commit()
    flash(f'Step "{s.name}" archived (data retained).', 'success')
    return redirect(url_for('main.admin'))

@bp.route('/admin/steps/rename', methods=['POST'])
def admin_rename_step():
    sid = int(request.form['step_id'])
    new_name = (request.form.get('name') or '').strip()
    if not new_name:
        flash('New name required', 'warning')
        return redirect(url_for('main.admin'))
    s = Step.query.get_or_404(sid)
    old = s.name
    s.name = new_name
    db.session.add(s); db.session.commit()
    flash(f'Renamed step "{old}" → "{new_name}"', 'success')
    return redirect(url_for('main.admin'))


@bp.route('/set-operator', methods=['POST'])
def set_operator():
    resp = make_response(redirect(request.referrer or url_for('main.index')))
    operator = (request.form.get('operator') or '').strip()
    resp.set_cookie('operator', operator, max_age=60*60*24*365)
    return resp
