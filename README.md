# Production Tracker

A lightweight, offline-friendly web application to track the assembly and testing status of hardware production runs.  
Designed for **factory floors** and **small batch assembly lines** where each unit has a unique QR/barcode.

- **Scan to update**: Plug in a USB barcode/QR scanner and scan units to bring up their status page.
- **Step tracking**: Define process steps (e.g. Kitting → Assembly → Programming → Test → Pack).
- **Pass/Fail/Reset**: Record results for each step, with timestamps, operator initials, and station name.
- **First-station auto-create**: Units can be automatically created when first scanned at the initial step.
- **Notes and audit log**: Keep operator notes and a full change history.
- **Admin tools**: Add/reorder/rename/archive steps, bulk import units from CSV, export status + notes to CSV.
- **Multi-station ready**: Multiple laptops/browsers can connect simultaneously over LAN.

---

## Screenshots

*(Add your own screenshots here: dashboard, scan page, unit detail page, admin page.)*

---

## Installation

### Requirements
- Python 3.10+
- pip
- A local or LAN-accessible machine to act as the server (Windows, Linux, macOS all supported)
- (Optional) USB barcode/QR scanner (acts as keyboard input)

---

### Windows Quick Start

Open **PowerShell** in the project folder (where `requirements.txt` lives):

```powershell
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate it
.\.venv\Scripts\Activate.ps1
# If blocked, run once: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialize the database (creates instance/production.sqlite3)
$env:FLASK_APP = "app"
flask db-init

# 5. Run the server
python -m waitress --listen=0.0.0.0:8000 app:app
