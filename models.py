from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'jawa' atau 'palembang'

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    performa = db.Column(db.String(20))
    tampilan = db.Column(db.String(20))
    tiket = db.Column(db.String(20))
    pembayaran = db.Column(db.String(20))
    akun = db.Column(db.String(20))
    # Hasil LLM Awal
    llm_jawa = db.Column(db.Text)
    llm_mix_jawa = db.Column(db.Text)
    llm_palembang = db.Column(db.Text)
    llm_mix_palembang = db.Column(db.Text)

class Annotation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey('review.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # Hasil Revisi Annotator
    rev_full = db.Column(db.Text)
    rev_mix = db.Column(db.Text)
    is_valid = db.Column(db.Boolean, default=True)