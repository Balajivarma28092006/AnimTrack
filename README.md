# **Anime Watchlist Tracker** 🎌  

A **secure**, **feature-rich** terminal application to track your anime progress, with encryption and statistics. Works on **Windows, macOS, and Linux**.  

---

## **Features** ✨  
✅ **Encrypted Storage** – Securely stores your data with AES-256  
✅ **Adult Content Protection** – Password-locked section for 18+ anime  
✅ **Statistics Dashboard** – Hours watched, completion rate, favorite genres  
✅ **Cross-Platform** – Runs anywhere (Terminal/CMD/PowerShell)  
✅ **Auto-Installer** – Automatically installs required dependencies  

---

## **Installation**  

### **Windows**  
#### **Method 1: One-Click Batch File**  
1. Download `my-anime-tracker.py`  
2. Create `anime-tracker.bat` in the same folder:  
   ```batch
   @echo off
   python my-anime-tracker.py
   pause
   ```
3. Double-click the `.bat` file to run!  

#### **Method 2: Manual Setup**  
```cmd
python -m pip install rich cryptography
python my-anime-tracker.py
```

---

### **Mac/Linux**  
```bash
# Make executable
chmod +x my-anime-tracker.py

# Run directly
./my-anime-tracker.py

# OR install globally
sudo cp my-anime-tracker.py /usr/local/bin/anime-tracker
anime-tracker  # Run from anywhere!
```

---

## **First-Time Setup** 🔒  
1. **Set a Master Password** (used to encrypt your data)  
2. **Optional**: Set an **Adult Content Password** (separate from the main password)  
3. **Save your Recovery Key** (critical if you forget passwords!)  

---

## **Commands** ⌨️  
| Command | Description |
|---------|-------------|
| `add` | Add new anime |
| `list` | Show your watchlist |
| `update` | Edit anime progress |
| `stats` | View watch statistics |
| `export` | Backup data to JSON |
| `adult` | Enter adult section (password required) |

---

## **Troubleshooting** 🔧  

### **"ModuleNotFoundError" (Missing Dependencies)**  
```cmd
pip install rich cryptography --user
```

### **"Python not found" (Windows)**  
- Reinstall Python from [python.org](https://python.org) **with "Add to PATH" checked**  

### **Batch File Closes Immediately**  
Add `pause` at the end of your `.bat` file:  
```batch
@echo off
python my-anime-tracker.py
pause
```

---

## **Backup & Data Location** 💾  
- **Config File**: `~/.Anime/config.json`  
- **Data File**: `~/.Anime/data.enc` (encrypted)  
- **Manual Backup**:  
  ```bash
  cp -r ~/.Anime ~/anime-backup
  ```

---

## **License**  
MIT License - Free for personal and commercial use.  

---

## **Support** ❤️  
**Found a bug?** Open an issue on [GitHub](https://github.com/Balajivarma28092006).    

---

🎉 **Happy Tracking!** 🎉  
 

--- 

📜 **Pro Tip**: Use `anime-tracker --help` for all commands!
