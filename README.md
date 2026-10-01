# Twilio Multi-Account Cleanup Script

This Python script automates the cleanup of unused Twilio Incoming Phone Numbers and Messaging Services across a master account and all associated active subaccounts. It reads a keep-list from a `table.tsv` file, protects designated resources, releases unlisted phone numbers, and deletes unlisted Messaging Services. All actions and errors are logged to a timestamped CSV file for auditing.

---

## Features

* **Multi-Account Sweeping:** Iterates through the main (parent) account and all active subaccounts automatically.
* **TSV Keep-List Protection:** Protects specified phone numbers and Messaging Service SIDs (`MG...`) listed in `table.tsv`.
* **Automatic Cascading Cleanup:** Releasing phone numbers automatically detaches them from messaging service sender pools.
* **CSV Audit Logging:** Exports execution details (Account Name, Resource SID, Action, Status, Error Details) to a timestamped log file (`cleanup_log_YYYYMMDD_HHMMSS.csv`) in both dry-run and live modes.
* **Dry-Run Safety Switch:** Runs in safe simulation mode (`dry_run=True`) by default to preview deletions without making live API calls.
* **Error Resilience:** Handles API errors and rate limits gracefully, allowing the script to continue processing remaining resources even if an individual deletion fails.

---

## Prerequisites

* Python 3.7+
* Master Twilio Account SID and Auth Token
* `table.tsv` file containing the numbers and messaging services to keep

---

## Step-by-Step Setup & Execution

### 1. Clone the Repository
```bash
git clone https://github.com/leo2298-twilio/twilio_cleanup_script.git
cd twilio_cleanup_script
```

### 2. Create a Virtual Environment
```bash
# macOS/Linux
python3 -m venv venv

# Windows
python -m venv venv
```

### 3. Activate the Virtual Environment
```bash
# macOS/Linux
source venv/bin/activate

# Windows (Command Prompt)
venv\Scripts\activate

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
```

### 4. Install Dependencies
Ensure `requirements.txt` includes `twilio>=8.0.0`, then install:
```bash
pip3 install -r requirements.txt
```

### 5. Prepare the Keep-List (`table.tsv`)
Place your `table.tsv` file in the project root directory. The file must use tab separation and include the following headers:

```text
Messaging Service	Numbers
MG3a619da627a26f7acc13de3b8cfd9302	+14848697461
MG36c63ce772973fad8b9b194db8bb86f6	+17208975588
MG0668c47aa9e35747dfb02dd1df0dc36c	+576013572758
	+18335151890
```

### 6. Set Environment Variables
Configure your Master Twilio credentials in your terminal session:

**macOS / Linux:**
```bash
export TWILIO_ACCOUNT_SID="your_master_account_sid"
export TWILIO_AUTH_TOKEN="your_master_auth_token"
```

**Windows (CMD):**
```cmd
set TWILIO_ACCOUNT_SID="your_master_account_sid"
set TWILIO_AUTH_TOKEN="your_master_auth_token"
```

**Windows (PowerShell):**
```powershell
$env:TWILIO_ACCOUNT_SID="your_master_account_sid"
$env:TWILIO_AUTH_TOKEN="your_master_auth_token"
```

---

## Running the Script

### Dry-Run Mode (Testing)
Run the script with `dry_run=True` (default setting) to generate a log of proposed actions without modifying your account:

```bash
python3 twilio_cleanup.py
```

Review the generated `cleanup_log_YYYYMMDD_HHMMSS.csv` file in your directory to confirm which numbers and services are marked for deletion versus retention.

### Production Execution (Live Deletion)
Once you have reviewed the CSV log and confirmed the actions:

1. Open `twilio_cleanup.py`.
2. Update the main execution call at the bottom of the script:
   ```python
   if __name__ == "__main__":
       clean_twilio_account(dry_run=False)
   ```
3. Execute the script:
   ```bash
   python3 twilio_cleanup.py
   ```

---

## Log File Format

The generated CSV log (`cleanup_log_YYYYMMDD_HHMMSS.csv`) contains eight columns:

| Column Header | Description |
| :--- | :--- |
| **Account Name** | Friendly name of the parent account or subaccount |
| **Account SID** | Account SID (`AC...`) |
| **Resource Type** | `Phone Number` or `Messaging Service` |
| **Friendly Name / Number** | Phone number string or Service Friendly Name |
| **Resource SID** | Twilio SID (`PN...` or `MG...`) |
| **Action** | `Keep` or `Delete` |
| **Status** | `SUCCESS`, `ERROR`, `DRY_RUN`, or `SKIPPED` |
| **Details** | Log description or API error message |