import pandas as pd
from app import db, User, Review, app
from werkzeug.security import generate_password_hash

def setup():
    with app.app_context():
        db.create_all()
        
        # 1. Tambah User (jika belum ada)
        if not User.query.filter_by(username='nals').first():
            nals = User(username='nals', password=generate_password_hash('jawa123'), role='jawa')
            fik = User(username='fik', password=generate_password_hash('palembang123'), role='palembang')
            db.session.add_all([nals, fik])
            db.session.commit()
            print("User nals & fik dibuat.")

        # 2. Tambah Data Review
        if Review.query.count() == 0:
            # Pastikan path file CSV sesuai (gunakan CSV yang sudah digabung kolom terjemahannya)
            df = pd.read_csv('/Users/nals/Documents/magister:3/kai-annotation-tool/dataset_website.csv').fillna('')
            
            for _, row in df.iterrows():
                rev = Review(
                    content=row['content'],
                    performa=row['Performa'],
                    tampilan=row['Tampilan'],
                    tiket=row['Tiket'],
                    pembayaran=row['Pembayaran'],
                    akun=row['Akun'],
                    # Masukkan semua varian terjemahan ke database
                    trans_jawa=row.get('trans_jawa', ''),
                    trans_mix_jawa=row.get('trans_mix_jawa', ''),
                    trans_palembang=row.get('trans_palembang', ''),
                    trans_mix_palembang=row.get('trans_mix_palembang', '')
                )
                db.session.add(rev)
            
            db.session.commit()
            print(f"{len(df)} data review berhasil diimport dari 1 CSV!")

if __name__ == '__main__':
    setup()