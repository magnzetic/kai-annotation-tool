import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kai-access-anotasi-2024'
db_url = os.getenv('DATABASE_URL')

if db_url:
    # Memaksa SQLAlchemy menggunakan driver psycopg2 alih-alih psycopg (psycopg3)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url if db_url else 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- WAJIB ADA: USER LOADER UNTUK FLASK-LOGIN ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.Text)  # <-- Menggunakan Text agar menampung hash apa pun tanpa batas
    role = db.Column(db.String(20))

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    performa = db.Column(db.String(50))
    tampilan = db.Column(db.String(50))
    tiket = db.Column(db.String(50))
    pembayaran = db.Column(db.String(50))
    akun = db.Column(db.String(50))
    
    trans_jawa = db.Column(db.Text)
    trans_mix_jawa = db.Column(db.Text)
    trans_palembang = db.Column(db.Text)
    trans_mix_palembang = db.Column(db.Text)
    
    annotations = db.relationship('Annotation', backref='review', lazy=True)

class Annotation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey('review.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # --- DIMENSI UNTUK FULL TEXT (Jawa / Palembang) ---
    acc_full = db.Column(db.Integer)       # Accuracy (1-3)
    acc_full_note = db.Column(db.Text)     # Opsional / catatan jika diperlukan
    
    acc_mix = db.Column(db.Integer)        # Acceptability (1-3)
    acc_mix_note = db.Column(db.Text)
    
    # Kita bisa rapikan namanya atau sesuaikan dengan 3 dimensi:
    # 1. Accuracy, 2. Acceptability, 3. Readability untuk Full
    acc_f = db.Column(db.Integer)  # Accuracy Full
    cep_f = db.Column(db.Integer)  # Acceptability Full
    rea_f = db.Column(db.Integer)  # Readability Full
    
    # --- DIMENSI UNTUK MIX TEXT (Indo-Jawa / Indo-Palembang) ---
    acc_m = db.Column(db.Integer)  # Accuracy Mix
    cep_m = db.Column(db.Integer)  # Acceptability Mix
    rea_m = db.Column(db.Integer)  # Readability Mix
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- OTOMATIS BUAT TABEL & USER DARI ENV VARIABLES ---
with app.app_context():
    db.create_all()
    
    # Jika tabel user masih kosong, buat user berdasarkan konfigurasi environment variable
    if User.query.count() == 0:
        # Format di Vercel: "username1:password1:role1,username2:password2:role2,..."
        users_config = os.getenv('USERS_CONFIG')
        
        if users_config:
            entries = users_config.split(',')
            for entry in entries:
                parts = entry.strip().split(':')
                if len(parts) == 3:
                    uname, upass, urole = parts[0], parts[1], parts[2]
                    hashed_pw = generate_password_hash(upass)
                    new_user = User(username=uname, password=hashed_pw, role=urole)
                    db.session.add(new_user)
            db.session.commit()
            print("✅ 4 User berhasil di-generate dari Environment Variables!")
        else:
            # Cadangan darurat jika USERS_CONFIG belum diset di Vercel
            print("⚠️ USERS_CONFIG belum diatur di Vercel Environment Variables!")

# --- ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Username atau password salah!', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    total = Review.query.count()
    done = Annotation.query.filter_by(user_id=current_user.id).count()
    percent = round((done / total) * 100, 1) if total > 0 else 0
    
    return render_template('dashboard.html', total=total, done=done, percent=percent)

@app.route('/history')
@login_required
def history():
    # Ambil semua data anotasi yang pernah dikerjakan oleh user ini
    annotations = Annotation.query.filter_by(user_id=current_user.id).all()
    return render_template('history.html', annotations=annotations)

@app.route('/edit/<int:annotation_id>', methods=['GET', 'POST'])
@login_required
def edit_annotation(annotation_id):
    anno = Annotation.query.get_or_404(annotation_id)
    # Pastikan hanya user bersangkutan yang bisa edit
    if anno.user_id != current_user.id:
        return redirect(url_for('history'))
        
    review = Review.query.get(anno.review_id)
    
    if request.method == 'POST':
        # Update nilai Full Translation
        anno.acc_f = request.form.get('acc_full', type=int)
        anno.cep_f = request.form.get('accept_full', type=int)
        anno.rea_f = request.form.get('read_full', type=int)
        
        # Update nilai Code-Mixed Translation
        anno.acc_m = request.form.get('acc_mix', type=int)
        anno.cep_m = request.form.get('accept_mix', type=int)
        anno.rea_m = request.form.get('read_mix', type=int)
        
        db.session.commit()
        return redirect(url_for('history'))
        
    return render_template('edit_annotate.html', anno=anno, review=review)

@app.route('/annotate')
@login_required
def annotate():
    done_ids = db.session.query(Annotation.review_id).filter(Annotation.user_id == current_user.id).all()
    done_ids = [r[0] for r in done_ids]
    
    item = Review.query.filter(~Review.id.in_(done_ids)).first()
    
    if not item:
        return render_template('finish.html')
        
    user_role = current_user.role
    return render_template('annotate.html', item=item, role=user_role)

@app.route('/annotate/<int:review_id>')
@login_required
def annotate_by_id(review_id):
    item = Review.query.get_or_404(review_id)
    user_role = current_user.role
    return render_template('annotate.html', item=item, role=user_role)

@app.route('/submit/<int:review_id>', methods=['POST'])
@login_required
def submit(review_id):
    new_anno = Annotation(
        review_id=review_id,
        user_id=current_user.id,
        acc_f=request.form.get('acc_full', type=int),
        cep_f=request.form.get('accept_full', type=int),
        rea_f=request.form.get('read_full', type=int),
        acc_m=request.form.get('acc_mix', type=int),
        cep_m=request.form.get('accept_mix', type=int),
        rea_m=request.form.get('read_mix', type=int)
    )
    db.session.add(new_anno)
    db.session.commit()
    return redirect(url_for('annotate'))

if __name__ == '__main__':
    app.run(debug=True)

import os
import pandas as pd

# --- OTOMATIS INISIALISASI DATABASE, USER, & CSV SAAT STARTUP ---
with app.app_context():
    db.create_all()
    
    # 1. Buat User otomatis jika tabel masih kosong
    if User.query.count() == 0:
        users_config = os.getenv('USERS_CONFIG')
        if users_config:
            for entry in users_config.split(','):
                parts = entry.strip().split(':')
                if len(parts) == 3:
                    uname, upass, urole = parts[0], parts[1], parts[2]
                    hashed_pw = generate_password_hash(upass)
                    db.session.add(User(username=uname, password=hashed_pw, role=urole))
            db.session.commit()
            print("✅ User default berhasil dibuat!")

    # 2. Import CSV otomatis dengan path absolut yang aman untuk Vercel
    if Review.query.count() == 0:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, 'dataset_website.csv')
        
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path).fillna('')
            for _, row in df.iterrows():
                rev = Review(
                    content=row.get('content', ''),
                    performa=row.get('Performa', ''),
                    tampilan=row.get('Tampilan', ''),
                    tiket=row.get('Tiket', ''),
                    pembayaran=row.get('Pembayaran', ''),
                    akun=row.get('Akun', ''),
                    trans_jawa=row.get('trans_jawa', ''),
                    trans_mix_jawa=row.get('trans_mix_jawa', ''),
                    trans_palembang=row.get('trans_palembang', ''),
                    trans_mix_palembang=row.get('trans_mix_palembang', '')
                )
                db.session.add(rev)
            db.session.commit()
            print(f"📦 Berhasil mengimport {len(df)} data review dari CSV!")
        else:
            print(f"⚠️ File CSV tidak ditemukan di path: {csv_path}")
