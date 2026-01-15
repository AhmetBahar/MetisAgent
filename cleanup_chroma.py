# cleanup_chroma.py
import shutil
import os

def clean_chroma_db():
    # ChromaDB dizini (varsayılan uygulama dizinindeki ./chroma_db)
    chroma_path = "./chroma_db"
    
    if os.path.exists(chroma_path):
        shutil.rmtree(chroma_path)
        print(f"ChromaDB dizini temizlendi: {chroma_path}")
    else:
        print(f"ChromaDB dizini bulunamadı: {chroma_path}")
    
    # Veri dizinini kontrol et ve temizle
    data_path = "./data"
    if os.path.exists(data_path):
        shutil.rmtree(data_path)
        print(f"Veri dizini temizlendi: {data_path}")
    else:
        print(f"Veri dizini bulunamadı: {data_path}")

if __name__ == "__main__":
    # Emin misiniz diye sor
    answer = input("Bu işlem tüm kullanıcı verilerini silecektir. Devam etmek istiyor musunuz? (e/h): ")
    
    if answer.lower() == 'e':
        clean_chroma_db()
        print("Temizleme tamamlandı. Şimdi uygulamayı yeniden başlatabilirsiniz.")
    else:
        print("İşlem iptal edildi.")