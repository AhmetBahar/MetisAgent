import subprocess
import platform

def execute_command(command):
    """
    İşletim sistemine uygun şekilde komut çalıştırır.
    
    Args:
        command (str): Çalıştırılacak komut.
    
    Returns:
        str: Komutun çıktısı veya hata mesajı.
    """
    system = platform.system()
    try:
        if system == "Windows":
            # Windows için komut çalıştırma
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
        else:
            # Linux/Unix için komut çalıştırma
            result = subprocess.run(f"bash -c '{command}'", shell=True, capture_output=True, text=True)
        
        # Başarılıysa stdout döndür, değilse stderr
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return f"Hata: {str(e)}"