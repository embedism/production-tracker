import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        SQLALCHEMY_DATABASE_URI="sqlite:///" + os.path.join(app.instance_path, "production.sqlite3"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        AUTO_CREATE_FIRST_STATION=bool(int(os.environ.get("AUTO_CREATE_FIRST_STATION", "1"))),
    )

    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)

    # --- lightweight schema upgrade for SQLite: ensure 'active' on step ---
    from sqlalchemy import inspect, text as sql_text
    with app.app_context():
        try:
            insp = inspect(db.engine)
            cols = [c['name'] if isinstance(c, dict) else c['name'] for c in insp.get_columns('step')]
            if 'active' not in cols:
                with db.engine.begin() as conn:
                    conn.execute(sql_text('ALTER TABLE step ADD COLUMN active BOOLEAN DEFAULT 1'))
        except Exception as e:
            app.logger.info(f'Schema check skipped/failed: {e}')

    from .models import Unit, Step, UnitStep, Audit  # noqa
    from .views import bp as main_bp
    app.register_blueprint(main_bp)

    @app.cli.command("db-init")
    def db_init():
        with app.app_context():
            db.create_all()
            from .models import Step
            if Step.query.count() == 0:
                steps_env = os.environ.get("STEPS")
                if steps_env:
                    names = [s.strip() for s in steps_env.split(",") if s.strip()]
                else:
                    names = ["Kitting", "Assembly", "Programming", "Test", "Pack"]
                for i, name in enumerate(names, start=1):
                    db.session.add(Step(name=name, sequence=i))
                db.session.commit()
                print("Initialized DB and seeded steps:", ", ".join(names))

    return app   # <-- MUST be indented inside create_app()

app = create_app()
