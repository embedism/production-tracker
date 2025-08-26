
from datetime import datetime
from . import db
from sqlalchemy import UniqueConstraint

class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    serial = db.Column(db.String(64), unique=True, nullable=False, index=True)
    meta_json = db.Column(db.Text, nullable=True)
    steps = db.relationship('UnitStep', back_populates='unit', cascade='all, delete-orphan')

class Step(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    sequence = db.Column(db.Integer, nullable=False, index=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    unit_steps = db.relationship('UnitStep', back_populates='step', cascade='all, delete-orphan')

class UnitStep(db.Model):
    __table_args__ = (UniqueConstraint('unit_id', 'step_id', name='uix_unit_step'),)
    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'), nullable=False)
    step_id = db.Column(db.Integer, db.ForeignKey('step.id'), nullable=False)
    status = db.Column(db.String(16), default='pending', nullable=False)  # pending, pass, fail
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    station = db.Column(db.String(64), nullable=True)
    operator = db.Column(db.String(64), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    unit = db.relationship('Unit', back_populates='steps')
    step = db.relationship('Step', back_populates='unit_steps')

class Audit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit_serial = db.Column(db.String(64), index=True, nullable=False)
    step_name = db.Column(db.String(64), nullable=False)
    old_status = db.Column(db.String(16), nullable=True)
    new_status = db.Column(db.String(16), nullable=False)
    station = db.Column(db.String(64), nullable=True)
    operator = db.Column(db.String(64), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
