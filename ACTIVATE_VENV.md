# Virtual Environment Aktif Etme Kılavuzu

## Windows Command Prompt (CMD) için:

```bash
venv\Scripts\activate.bat
```

## Windows PowerShell için:

```bash
venv\Scripts\activate.ps1
```

**Not:** PowerShell'de ExecutionPolicy hatası alırsanız:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Hızlı Kullanım

Her yeni terminal açtığınızda:

1. Proje klasörüne gidin:
   ```bash
   cd "C:\Users\yener\Desktop\Company Discovery Agent"
   ```

2. Venv'i aktif edin:
   - **CMD için:** `venv\Scripts\activate.bat`
   - **PowerShell için:** `venv\Scripts\activate.ps1`

3. Aktif olduğunu kontrol edin (prompt'ta `(venv)` görünür):
   ```bash
   python --version
   pip list
   ```

## Deaktif Etme

```bash
deactivate
```

## Alternatif: Doğrudan Python Kullanımı

Venv'i aktif etmeden de doğrudan kullanabilirsiniz:

```bash
venv\Scripts\python.exe -m pip list
venv\Scripts\python.exe main.py
```

