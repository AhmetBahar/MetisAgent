#!/usr/bin/env python3
"""
Metis Agent Kurulum Scripti
Bu script, Metis Agent'ın farklı platformlarda (Windows, Linux, WSL) kurulumunu otomatize eder.
"""
import os
import sys
import platform
import subprocess
import argparse
from pathlib import Path

def is_wsl():
    """WSL ortamını kontrol eder"""
    if os.path.exists('/proc/version'):
        with open('/proc/version', 'r') as f:
            if 'microsoft' in f.read().lower():
                return True
    return False

def run_command(cmd, shell=True):
    """Komut çalıştırır ve çıktıyı döndürür"""
    print(f"Çalıştırılıyor: {cmd}")
    try:
        result = subprocess.run(cmd, shell=shell, check=True, text=True, capture_output=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Hata: {e}")
        print(f"Çıktı: {e.stdout}")
        print(f"Hata çıktısı: {e.stderr}")
        return None

def check_conda():
    """Conda'nın kurulu olup olmadığını kontrol eder"""
    try:
        run_command("conda --version")
        return True
    except Exception:
        return False

def install_conda():
    """Conda'yı sistemde kurulu değilse kurar"""
    system = platform.system()
    
    print("Conda kurulu değil. Kurulum başlatılıyor...")
    
    if system == "Windows":
        # Windows için Miniconda kurulumu
        run_command("curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe")
        run_command("start /wait \"\" Miniconda3-latest-Windows-x86_64.exe /InstallationType=JustMe /RegisterPython=0 /S /D=%UserProfile%\\Miniconda3")
        os.remove("Miniconda3-latest-Windows-x86_64.exe")
    else:
        # Linux/WSL için Miniconda kurulumu
        run_command("curl -sL https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o miniconda.sh")
        run_command("bash miniconda.sh -b -p $HOME/miniconda")
        run_command("rm miniconda.sh")
        
        # Path'e ekleme
        home_dir = str(Path.home())
        conda_path = os.path.join(home_dir, "miniconda", "bin")
        
        shell_rc = None
        if os.path.exists(os.path.join(home_dir, ".bashrc")):
            shell_rc = os.path.join(home_dir, ".bashrc")
        elif os.path.exists(os.path.join(home_dir, ".zshrc")):
            shell_rc = os.path.join(home_dir, ".zshrc")
            
        if shell_rc:
            with open(shell_rc, "a") as f:
                f.write(f'\n# Miniconda\nexport PATH="{conda_path}:$PATH"\n')
            print(f"{shell_rc} dosyasına Conda path eklendi.")
            
        print(f"Conda kurulumu tamamlandı. Sistemi yeniden başlatın ve '{conda_path}/conda' komutunu kullanabilirsiniz.")
        sys.exit(0)

def setup_env(env_name, python_version):
    """Conda environment oluşturur ve gerekli paketleri kurar"""
    # Environment oluşturma
    run_command(f"conda create -n {env_name} python={python_version} -y")
    
    # Environment aktivasyonu ve komut çalıştırma için bash kullanımı
    conda_base = run_command("conda info --base").strip()
    
    # Komutlar için bash script oluştur
    with open("setup_commands.sh", "w") as f:
        f.write(f"""#!/bin/bash
source "{conda_base}/etc/profile.d/conda.sh"
conda activate {env_name}

# Temel paketleri conda ile kurma
conda install -c conda-forge flask requests psutil -y

# Flask ve web ilişkili paketler
pip install flask-cors flask-sock flask-socketio

# Selenium ve ilgili araçlar
pip install selenium webdriver-manager

# LLM API entegrasyonları
pip install openai anthropic google-generativeai deepseek-ai

# WebSocket ve asenkron destek
pip install gevent websockets

# Platform özel paketler
{f'pip install python-prctl' if platform.system() != 'Windows' else ''}
{f'pip install pywin32' if platform.system() == 'Windows' else ''}

# Geliştirme araçları
pip install pytest black flake8 isort

# Requirements.txt oluşturma 
pip freeze > requirements.txt
echo "Kurulum başarıyla tamamlandı!"
""")
    
    # Bash scripti çalıştırılabilir yap ve çalıştır
    run_command("chmod +x setup_commands.sh")
    result = run_command("bash ./setup_commands.sh")
    run_command("rm setup_commands.sh")
    
    if result is not None:
        print(f"\n{env_name} environment kurulumu tamamlandı!")
        print(f"Etkinleştirmek için: conda activate {env_name}")
        return True
    else:
        print(f"\n{env_name} environment kurulumu sırasında hatalar oluştu.")
        return False

def setup_browser_drivers():
    """Platform uygun tarayıcı sürücülerini kurar"""
    system = platform.system()
    is_wsl_env = is_wsl()
    
    print("\nTarayıcı sürücüleri kurulumu başlatılıyor...")
    
    if system == "Windows" or is_wsl_env:
        # Windows veya WSL için Chrome WebDriver kurulumu
        print("Chrome WebDriver için automatic-manager kullanılacak. Python kodunda şu şekilde kullanabilirsiniz:")
        print("""
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
if is_wsl():  # WSL kontrolü
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
        """)
    
    if system == "Linux" or is_wsl_env:
        # Linux/WSL için gerekli paketleri kurma
        try:
            if is_wsl_env:
                print("\nWSL ortamı tespit edildi. Chrome kurulumu için şu adımları takip edebilirsiniz:")
                print("""
# WSL üzerinde Chrome kurulumu:
sudo apt update
sudo apt install -y wget curl gnupg
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install -y google-chrome-stable
                """)
            else:
                # Normal Linux için Chrome kurulum talimatları
                print("\nLinux ortamı tespit edildi. Chrome kurulumu için şu adımları takip edebilirsiniz:")
                print("""
# Linux üzerinde Chrome kurulumu:
sudo apt update
sudo apt install -y wget curl gnupg
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install -y google-chrome-stable
                """)
        except Exception as e:
            print(f"Linux paketleri kurulurken hata oluştu: {e}")
    
    print("\nTarayıcı sürücüleri kurulumu tamamlandı.")

def main():
    parser = argparse.ArgumentParser(description="Metis Agent Kurulum Scripti")
    parser.add_argument("--env-name", default="metis-agent", help="Oluşturulacak conda environment adı")
    parser.add_argument("--python-version", default="3.9", help="Kullanılacak Python versiyonu")
    args = parser.parse_args()
    
    print("\nMetis Agent Kurulum Scripti")
    print("--------------------------")
    print(f"Platform: {platform.system()} {platform.release()}")
    if is_wsl():
        print("WSL ortamı tespit edildi.")
    
    # Conda kurulumunu kontrol et
    if not check_conda():
        install_conda()
    
    # Environment kurulumu
    setup_env(args.env_name, args.python_version)
    
    # Tarayıcı sürücüleri kurulumu
    setup_browser_drivers()
    
    print("\nKurulum tamamlandı!")
    print(f"Metis Agent'ı kullanmak için: conda activate {args.env_name}")
    print("Ardından 'python app.py' komutu ile uygulamayı başlatabilirsiniz.")

if __name__ == "__main__":
    main()