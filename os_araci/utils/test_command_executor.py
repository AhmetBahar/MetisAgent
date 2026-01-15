from command_executor import execute_command

def test_command_executor():
    # İşletim sistemi kontrolü
    import platform
    system = platform.system()

    print("Testing on:", system)

    # Test 1: Çalışma dizinini listeleme
    print("\nTest 1: Dosya listeleme")
    command = "dir" if system == "Windows" else "ls"
    result = execute_command(command)
    print("Output:\n", result)

    # Test 2: Çalışma dizinini görüntüleme
    print("\nTest 2: Çalışma dizinini görüntüleme")
    command = "cd" if system == "Windows" else "pwd"
    result = execute_command(command)
    print("Output:\n", result)

    # Test 3: Hatalı bir komut
    print("\nTest 3: Hatalı komut")
    command = "invalid_command"
    result = execute_command(command)
    print("Output:\n", result)

# Testleri çalıştır
if __name__ == "__main__":
    test_command_executor()
