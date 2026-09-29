import pandas as pd
from app import db, Review, app

def import_csv():
    with app.app_context():
        db.drop_all() # Reset DB jika ingin mulai baru
        db.create_all()
        
        # Baca dataset
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, 'dataset_website.csv')
        df = pd.read_csv(csv_path)
        
        # Bersihkan NaN agar tidak error saat masuk DB
        df = df.fillna('')

        for _, row in df.iterrows():
            new_review = Review(
                content=row['content'],
                performa=row['Performa'],
                tampilan=row['Tampilan'],
                tiket=row['Tiket'],
                pembayaran=row['Pembayaran'],
                akun=row['Akun'],
                # Simulasi kolom terjemahan (Ganti dengan nama kolom di CSV Anda jika sudah ada)
                trans_jawa=row.get('trans_jawa', '[BELUM DITRANSLATE]'),
                trans_mix_jawa=row.get('trans_mix_jawa', '[BELUM DITRANSLATE]'),
                trans_palembang=row.get('trans_palembang', '[BELUM DITRANSLATE]'),
                trans_mix_palembang=row.get('trans_mix_palembang', '[BELUM DITRANSLATE]')
            )
            db.session.add(new_review)
        
        db.session.commit()
        print(f"Berhasil mengimpor {len(df)} data.")

if __name__ == '__main__':
    import_csv()
