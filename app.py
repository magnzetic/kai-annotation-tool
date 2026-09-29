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

# --- MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20)) # 'jawa' or 'palembang'

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
    
    status_full = db.Column(db.String(20), default='valid') 
    rev_full = db.Column(db.Text)
    
    status_mix = db.Column(db.String(20), default='valid')
    rev_mix = db.Column(db.Text)
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- OTOMATIS BUAT TABEL DI SUPABASE SAAT STARTUP ---
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
        anno.status_full = request.form.get('option_full')
        anno.rev_full = request.form.get('rev_full') if anno.status_full == 'revise' else review.trans_jawa
        
        anno.status_mix = request.form.get('option_mix')
        anno.rev_mix = request.form.get('rev_mix') if anno.status_mix == 'revise' else review.trans_mix_jawa
        
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
        status_full=request.form.get('option_full'),
        rev_full=request.form.get('rev_full') if request.form.get('option_full') == 'revise' else None,
        status_mix=request.form.get('option_mix'),
        rev_mix=request.form.get('rev_mix') if request.form.get('option_mix') == 'revise' else None
    )
    db.session.add(new_anno)
    db.session.commit()
    return redirect(url_for('annotate'))

if __name__ == '__main__':
    app.run(debug=True)
