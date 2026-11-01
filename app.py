import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kai-access-anotasi-2024'
db_url = os.getenv('DATABASE_URL')

if db_url:
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url if db_url else 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.Text)
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
    
    # 3 Dimensi Full
    acc_f = db.Column(db.Integer)
    cep_f = db.Column(db.Integer)
    rea_f = db.Column(db.Integer)
    rev_full = db.Column(db.Text)
    
    # 3 Dimensi Mix
    acc_m = db.Column(db.Integer)
    cep_m = db.Column(db.Integer)
    rea_m = db.Column(db.Integer)
    rev_mix = db.Column(db.Text)
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

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
    # Target total selalu 1000 untuk setiap annotator
    total = 1000
    done = Annotation.query.filter_by(user_id=current_user.id).count()
    percent = round((done / total) * 100, 1) if total > 0 else 0
    
    return render_template('dashboard.html', total=total, done=done, percent=percent)

@app.route('/history')
@login_required
def history():
    annotations = Annotation.query.filter_by(user_id=current_user.id).all()
    return render_template('history.html', annotations=annotations)

@app.route('/edit/<int:annotation_id>', methods=['GET', 'POST'])
@login_required
def edit_annotation(annotation_id):
    anno = Annotation.query.get_or_404(annotation_id)
    if anno.user_id != current_user.id:
        return redirect(url_for('history'))
        
    review = Review.query.get(anno.review_id)
    
    if request.method == 'POST':
        need_rev_full = request.form.get('need_rev_full')
        anno.rev_full = request.form.get('rev_full') if need_rev_full == 'yes' else ''
        
        anno.acc_f = request.form.get('acc_full', type=int)
        anno.cep_f = request.form.get('accept_full', type=int)
        anno.rea_f = request.form.get('read_full', type=int)
        
        need_rev_mix = request.form.get('need_rev_mix')
        anno.rev_mix = request.form.get('rev_mix') if need_rev_mix == 'yes' else ''
        
        anno.acc_m = request.form.get('acc_mix', type=int)
        anno.cep_m = request.form.get('accept_mix', type=int)
        anno.rea_m = request.form.get('read_mix', type=int)
        
        db.session.commit()
        return redirect(url_for('history'))
        
    user_role = current_user.role
    return render_template('edit_annotate.html', anno=anno, review=review, role=user_role)

@app.route('/annotate')
@login_required
def annotate():
    done_ids = db.session.query(Annotation.review_id).filter(Annotation.user_id == current_user.id).all()
    done_ids = [r[0] for r in done_ids]
    
    # Ambil data review yang belum dikerjakan oleh user ini, batasi dari 1000 data pertama
    item = Review.query.filter(~Review.id.in_(done_ids)).order_by(Review.id.asc()).first()
    
    # Jika sudah selesai 1000 data, arahkan ke halaman penutup (finish.html / thank you)
    if not item or Review.query.filter(Review.id.in_(done_ids)).count() >= 1000:
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
    review = Review.query.get_or_404(review_id)
    
    # Cek apakah sudah pernah menganotasi review ini sebelumnya
    existing_anno = Annotation.query.filter_by(review_id=review_id, user_id=current_user.id).first()
    
    if existing_anno:
        # Jika sudah ada, update datanya
        existing_anno.acc_f = request.form.get('acc_full', type=int)
        existing_anno.cep_f = request.form.get('accept_full', type=int)
        existing_anno.rea_f = request.form.get('read_full', type=int)
        existing_anno.rev_full = request.form.get('rev_full') or (review.trans_jawa if current_user.role == 'jawa' else review.trans_palembang)
        
        existing_anno.acc_m = request.form.get('acc_mix', type=int)
        existing_anno.cep_m = request.form.get('accept_mix', type=int)
        existing_anno.rea_m = request.form.get('read_mix', type=int)
        existing_anno.rev_mix = request.form.get('rev_mix') or (review.trans_mix_jawa if current_user.role == 'jawa' else review.trans_mix_palembang)
    else:
        # Jika belum, buat baru
        new_anno = Annotation(
            review_id=review_id,
            user_id=current_user.id,
            acc_f=request.form.get('acc_full', type=int),
            cep_f=request.form.get('accept_full', type=int),
            rea_f=request.form.get('read_full', type=int),
            rev_full=request.form.get('rev_full') or (review.trans_jawa if current_user.role == 'jawa' else review.trans_palembang),
            
            acc_m=request.form.get('acc_mix', type=int),
            cep_m=request.form.get('accept_mix', type=int),
            rea_m=request.form.get('read_mix', type=int),
            rev_mix=request.form.get('rev_mix') or (review.trans_mix_jawa if current_user.role == 'jawa' else review.trans_mix_palembang)
        )
        db.session.add(new_anno)
        
    db.session.commit()
    return redirect(url_for('annotate'))

# --- OTOMATIS INISIALISASI DATABASE KUNCI PAS 1000 ---
with app.app_context():
    db.create_all()
    
    # 1. Buat User otomatis jika tabel user masih kosong
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

    # 2. Import CSV dikunci mutlak tepat 1000 baris pertama saja
    total_reviews = Review.query.count()
    if total_reviews < 1000:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, 'dataset_website.csv')
        
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path).fillna('').head(1000)
            
            needed = 1000 - total_reviews
            df_to_insert = df.tail(needed) if total_reviews > 0 else df
            
            for _, row in df_to_insert.iterrows():
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
            print(f"✅ Selesai! Total review dikunci tepat di angka 1000.")
        else:
            print(f"⚠️ File CSV tidak ditemukan di path: {csv_path}")

if __name__ == '__main__':
    app.run(debug=True)
