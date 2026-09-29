import os
import pandas as pd
from app import db, User, Review, app
from werkzeug.security import generate_password_hash

def setup():
    with app.app_context():
        db.create_all()
        
        # Ambil konfigurasi user rahasia dari environment variable
        # Format string di Vercel nanti: "user1:pass1:jawa,user2:pass2:jawa,user3:pass3:palembang,user4:pass4:palembang"
        users_env = os.getenv('USERS_CONFIG')
        
        if users_env:
            # Parsing data user secara dinamis dari environment variable
            user_entries = users_env.split(',')
            for entry in user_entries:
                parts = entry.strip().split(':')
                if len(parts) == 3:
                    uname, upass, urole = parts[0], parts[1], parts[2]
                    
                    # Cek apakah user sudah ada di database
                    if not User.query.filter_by(username=uname).first():
                        hashed_pw = generate_password_hash(upass)
                        new_user = User(username=uname, password=hashed_pw, role=urole)
                        db.session.add(new_user)
                        print(f"✅ User '{uname}' dengan role '{urole}' berhasil dibuat.")
            
            db.session.commit()
        else:
            print("⚠️ Peringatan: USERS_CONFIG belum diatur di Environment Variables!")

        # 2. Tambah Data Review dari CSV
        if Review.query.count() == 0:
            csv_path = os.getenv('CSV_FILE_PATH', 'dataset_website.csv')
            
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path).fillna('')
                
                for _, row in df.iterrows():
                    rev = Review(
                        content=row['content'],
                        performa=row['Performa'],
                        tampilan=row['Tampilan'],
                        tiket=row['Tiket'],
                        pembayaran=row['Pembayaran'],
                        akun=row['Akun'],
                        trans_jawa=row.get('trans_jawa', ''),
                        trans_mix_jawa=row.get('trans_mix_jawa', ''),
                        trans_palembang=row.get('trans_palembang', ''),
                        trans_mix_palembang=row.get('trans_mix_palembang', '')
                    )
                    db.session.add(rev)
                
                db.session.commit()
                print(f"📦 {len(df)} data review berhasil diimport dari {csv_path}!")
            else:
                print(f"⚠️ File CSV '{csv_path}' tidak ditemukan!")

if __name__ == '__main__':
    setup()
