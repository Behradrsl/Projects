# Command Line Cheat Sheet

> A quick reference for essential terminal commands on macOS and Linux.

## 1. Navigating the File System

Commands for moving between folders and locating files.

| Command | Description |
|---------|-------------|
| `pwd` | Show the current directory path |
| `ls` | List files and folders |
| `ls -la` | List all files, including hidden ones |
| `cd Documents` | Enter the Documents folder |
| `cd ..` | Move up one directory |
| `cd ~` | Go to the home directory |
| `cd /` | Go to the root directory |
| `cd -` | Return to the previous directory |

### Example

```bash
pwd                 # Check current location
ls                  # See available files
cd Documents        # Enter Documents
cd ..               # Return to parent folder
```

---

## 2. Working with Files and Directories

Commands for creating, copying, moving, and deleting files.

| Command | Description |
|---------|-------------|
| `mkdir new_folder` | Create a directory |
| `touch file.txt` | Create an empty file |
| `rm file.txt` | Delete a file |
| `rm -r folder` | Delete a folder and its contents |
| `rmdir empty_folder` | Delete an empty directory |
| `cp file.txt copy.txt` | Copy a file |
| `cp -r folder backup` | Copy a directory |
| `mv file.txt folder/` | Move a file |
| `mv old.txt new.txt` | Rename a file |

> **Warning:** `rm` permanently removes files in normal terminal usage. Use it carefully.

### Example

```bash
mkdir PythonProject          # Create project folder
cd PythonProject             # Enter the folder
touch main.py                # Create Python file
cp main.py backup.py         # Make a backup
mv backup.py old_main.py     # Rename backup
ls                           # Check files
```

---

## 3. Viewing Files

| Command | Description |
|---------|-------------|
| `cat file.txt` | Display file contents |
| `less file.txt` | Read a file page by page |
| `head file.txt` | Display first 10 lines |
| `tail file.txt` | Display last 10 lines |

> Press `q` to exit the `less` viewer.

---

## 4. Useful Terminal Commands

| Command | Description |
|---------|-------------|
| `history` | Show previously executed commands |
| `clear` | Clear the terminal screen |
| `which python3` | Find the location of Python |
| `man ls` | Open the manual for `ls` |
| `whoami` | Display the current username |
| `echo "Hello"` | Print text in the terminal |

---

## 5. Downloading Files

### curl

Transfers data to or from a server. Available by default on macOS.

```bash
# Download a file
curl -O https://example.com/file.txt

# Download with a custom filename
curl -o myfile.txt https://example.com/file.txt
```

### wget

Downloads files from the web.

```bash
wget https://example.com/file.txt
```

> **Note:** `wget` may require separate installation on macOS.

---

## 6. Running Python

| Command | Description |
|---------|-------------|
| `python3 --version` | Check Python version |
| `python3 main.py` | Run a Python script |
| `python3` | Open interactive Python |
| `python3 -m pip install numpy` | Install a package |
| `python3 -m venv .venv` | Create a virtual environment |
| `source .venv/bin/activate` | Activate the virtual environment |
| `deactivate` | Exit the virtual environment |

---

## 7. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Tab` | Auto-complete filenames and commands |
| `↑ / ↓` | Browse command history |
| `Ctrl + C` | Stop the running command |
| `
