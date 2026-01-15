import requests
import os

BASE_URL = "http://localhost:5000/file"

def test_file_manager():
    # Test 1: Dosya listeleme
    print("\nTest 1: Dosya Listeleme")
    response = requests.get(f"{BASE_URL}/list", params={"path": "."})
    print("Status Code:", response.status_code)
    print("Response:", response.json())

    # Test 2: Klasör oluşturma
    print("\nTest 2: Klasör Oluşturma")
    response = requests.post(f"{BASE_URL}/create_folder", json={"path": "./test_folder"})
    print("Status Code:", response.status_code)
    print("Response:", response.json())

    # Test 3: Dosya oluşturma
    print("\nTest 3: Dosya Oluşturma")
    response = requests.post(f"{BASE_URL}/create_file", json={"path": "./test_folder/test_file.txt", "content": "Merhaba Dünya!"})
    print("Status Code:", response.status_code)
    print("Response:", response.json())

    # Test 4: Klasör listeleme
    print("\nTest 4: Klasör Listeleme")
    response = requests.get(f"{BASE_URL}/list_folders", params={"path": "."})
    print("Status Code:", response.status_code)
    print("Response:", response.json())

    # Test 5: Çalışma dizinini değiştirme
    print("\nTest 5: Çalışma Dizinini Değiştirme")
    response = requests.post(f"{BASE_URL}/change_directory", json={"path": "./test_folder"})
    print("Status Code:", response.status_code)
    print("Response:", response.json())

    # Test 6: Dosya silme
    print("\nTest 6: Dosya Silme")
    response = requests.delete(f"{BASE_URL}/delete", json={"path": "./test_folder/test_file.txt"})
    print("Status Code:", response.status_code)
    print("Response:", response.json())

    # Test 7: Klasör silme
    print("\nTest 7: Klasör Silme")
    response = requests.delete(f"{BASE_URL}/delete_folder", json={"path": "./test_folder"})
    print("Status Code:", response.status_code)
    print("Response:", response.json())

if __name__ == "__main__":
    test_file_manager()
