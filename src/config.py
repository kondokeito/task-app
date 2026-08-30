from sqlalchemy.orm import DeclarativeBase
from flask_sqlalchemy import SQLAlchemy


class Base(DeclarativeBase):
    pass


# トップレベルで db インスタンスを生成（これで model.py から import 可能になります）
db = SQLAlchemy(model_class=Base)

POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "postgres"
POSTGRES_HOSTNAME = "db"


def init_sql_alchemy(app):
    app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOSTNAME}"

    # アプリケーションに対して db を初期化
    db.init_app(app)
