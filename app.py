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
    
    # Fase 1: Monolingual (Tanpa word_tags_mono)
    acc_f = db.Column(db.Integer)
    cep_f = db.Column(db.Integer)
    rea_f = db.Column(db.Integer)
    rev_full = db.Column(db.Text)
    
    # Fase 2: Code-Mixed
    acc_m = db.Column(db.Integer)
    cep_m = db.Column(db.Integer)
    rea_m = db.Column(db.Integer)
    rev_mix = db.Column(db.Text)
    word_tags_mix = db.Column(db.Text)
    
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
    total_mono = 1000
    done_mono = Annotation.query.filter(Annotation.user_id == current_user.id, Annotation.acc_f.isnot(None)).count()
    
    total_mix = 1000
    done_mix = Annotation.query.filter(Annotation.user_id == current_user.id, Annotation.acc_m.isnot(None)).count()
    
    percent_mono = round((done_mono / total_mono) * 100, 1) if total_mono > 0 else 0
    percent_mix = round((done_mix / total_mix) * 100, 1) if total_mix > 0 else 0
    
    return render_template('dashboard.html', 
                           total_mono=total_mono, done_mono=done_mono, percent_mono=percent_mono,
                           total_mix=total_mix, done_mix=done_mix, percent_mix=percent_mix)

@app.route('/history')
@login_required
def history():
    annotations = Annotation.query.filter_by(user_id=current_user.id).all()
    
    reviews_with_status = []
    for anno in annotations:
        rev = Review.query.get(anno.review_id)
        if rev:
            reviews_with_status.append({
                'review': rev,
                'anno': anno
            })
            
    return render_template('history.html', reviews_with_status=reviews_with_status)
    
@app.route('/edit/monolingual/<int:review_id>', methods=['GET', 'POST'])
@login_required
def edit_monolingual(review_id):
    review = Review.query.get(review_id)
    if not review:
        flash('Data review tidak ditemukan!', 'danger')
        return redirect(url_for('history'))
        
    anno = Annotation.query.filter_by(review_id=review.id, user_id=current_user.id).first()
    if not anno:
        anno = Annotation(review_id=review.id, user_id=current_user.id)
        db.session.add(anno)
        db.session.commit()
    
    if request.method == 'POST':
        anno.acc_f = request.form.get('acc_full', type=int)
        anno.cep_f = request.form.get('accept_full', type=int)
        anno.rea_f = request.form.get('read_full', type=int)
        
        need_rev = request.form.get('need_rev_full')
        if need_rev == 'yes':
            anno.rev_full = request.form.get('rev_full')
        else:
            anno.rev_full = None
            
        db.session.commit()
        flash('Anotasi Monolingual berhasil diperbarui!', 'success')
        return redirect(url_for('history'))
        
    return render_template('edit_mono.html', review=review, anno=anno)

@app.route('/edit/codemixed/<int:review_id>', methods=['GET', 'POST'])
@login_required
def edit_codemixed(review_id):
    review = Review.query.get_or_404(review_id)
    anno = Annotation.query.filter_by(review_id=review.id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        anno.acc_m = request.form.get('acc_mix', type=int)
        anno.cep_m = request.form.get('accept_mix', type=int)
        anno.rea_m = request.form.get('read_mix', type=int)
        
        need_rev = request.form.get('need_rev_mix')
        if need_rev == 'yes':
            anno.rev_mix = request.form.get('rev_mix')
        else:
            anno.rev_mix = None
            
        word_tags_mix = request.form.get('word_tags_json')
        if word_tags_mix:
            anno.word_tags_mix = word_tags_mix
            
        db.session.commit()
        flash('Anotasi Code-Mixed berhasil diperbarui!', 'success')
        return redirect(url_for('history'))
        
    user_role = current_user.role
    return render_template('edit_mix.html', anno=anno, review=review, role=user_role)

@app.route('/annotate')
@login_required
def annotate():
    done_mono = Annotation.query.filter(Annotation.user_id == current_user.id, Annotation.acc_f.isnot(None)).count()
    if done_mono < 1000:
        return redirect(url_for('annotate_monolingual'))
    else:
        return redirect(url_for('annotate_codemixed'))

@app.route('/annotate/monolingual')
@login_required
def annotate_monolingual():
    done_count = Annotation.query.filter(
        Annotation.user_id == current_user.id, 
        Annotation.acc_f.isnot(None)
    ).count()
    
    # Mengarah ke transition_codemixed yang benar
    if done_count >= 1000:
        return redirect(url_for('transition_codemixed'))
    
    item = Review.query.order_by(Review.id.asc()).offset(done_count).first()
    
    if not item:
        return redirect(url_for('transition_codemixed'))
        
    user_role = current_user.role
    return render_template('annotate_mono.html', item=item, role=user_role)

@app.route('/submit/monolingual/<int:review_id>', methods=['POST'])
@login_required
def submit_monolingual(review_id):
    review = Review.query.get_or_404(review_id)
    
    anno = Annotation.query.filter_by(review_id=review_id, user_id=current_user.id).first()
    if not anno:
        anno = Annotation(review_id=review_id, user_id=current_user.id)
        db.session.add(anno)
        
    # Menangkap nama input dari form HTML
    anno.acc_f = request.form.get('acc_full', type=int)
    anno.cep_f = request.form.get('accept_full', type=int)
    anno.rea_f = request.form.get('read_full', type=int)
    
    need_rev = request.form.get('need_rev_full')
    if need_rev == 'yes':
        anno.rev_full = request.form.get('rev_full')
    else:
        anno.rev_full = None
    
    db.session.commit()
    
    total_done = Annotation.query.filter(
        Annotation.user_id == current_user.id, 
        Annotation.acc_f.isnot(None)
    ).count()
    
    # Mengarah ke transition_codemixed yang benar
    if total_done >= 1000:
        return redirect(url_for('transition_codemixed'))
        
    return redirect(url_for('annotate_monolingual'))
    
@app.route('/transition/codemixed')
@login_required
def transition_codemixed():
    return render_template('transition_mix.html')

@app.route('/annotate/codemixed')
@login_required
def annotate_codemixed():
    done_mono_count = Annotation.query.filter(Annotation.user_id == current_user.id, Annotation.acc_f.isnot(None)).count()
    if done_mono_count < 1000:
        flash('⚠️ Anda harus menyelesaikan 1000 data Monolingual terlebih dahulu!', 'warning')
        return redirect(url_for('annotate_monolingual'))

    done_mix_ids = db.session.query(Annotation.review_id).filter(Annotation.user_id == current_user.id, Annotation.acc_m.isnot(None)).all()
    done_mix_ids = [r[0] for r in done_mix_ids]
    
    item = Review.query.filter(~Review.id.in_(done_mix_ids)).order_by(Review.id.asc()).first()
    
    if not item or Review.query.filter(Review.id.in_(done_mix_ids)).count() >= 1000:
        return render_template('finish.html')
        
    user_role = current_user.role
    return render_template('annotate_mix.html', item=item, role=user_role)

@app.route('/submit/codemixed/<int:review_id>', methods=['POST'])
@login_required
def submit_codemixed(review_id):
    review = Review.query.get_or_404(review_id)
    
    anno = Annotation.query.filter_by(review_id=review_id, user_id=current_user.id).first()
    if not anno:
        anno = Annotation(review_id=review_id, user_id=current_user.id)
        db.session.add(anno)
        
    anno.acc_m = request.form.get('acc_mix', type=int)
    anno.cep_m = request.form.get('accept_mix', type=int)
    anno.rea_m = request.form.get('read_mix', type=int)
    anno.rev_mix = request.form.get('rev_mix') or (review.trans_mix_jawa if current_user.role == 'jawa' else review.trans_mix_palembang)
    anno.word_tags_mix = request.form.get('word_tags_json', '')
    
    db.session.commit()
    return redirect(url_for('annotate_codemixed'))

with app.app_context():
    db.create_all()
    if User.query.count() == 0:
        users_config = os.getenv('USERS_CONFIG')
        if users_config:
            for entry in users_config.split(','):
                parts = entry.strip().split(':')
                if len(parts) == 3:
                    uname, upass, urole = parts[0], parts[1], parts[2]
                    db.session.add(User(username=uname, password=generate_password_hash(upass), role=urole))
            db.session.commit()

    if Review.query.first() is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, 'dataset_website.csv')
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path).fillna('').head(1000)
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

if __name__ == '__main__':
    app.run(debug=True)
