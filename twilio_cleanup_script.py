import os
import csv
import re
from datetime import datetime
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')

def load_keep_lists(filepath="table.tsv"):
    numbers_to_keep = set()
    services_to_keep = set()
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            svc = row.get('Messaging Service', '').strip()
            if svc.startswith('MG'):
                services_to_keep.add(svc)
                
            num_raw = row.get('Numbers', '').strip()
            match = re.search(r'\d+', num_raw)
            if match:
                num = match.group()
                if len(num) >= 10 and not num.startswith('+'):
                    num = '+' + num
                numbers_to_keep.add(num)
                
    return numbers_to_keep, services_to_keep

def clean_twilio_account(dry_run=True):
    master_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    try:
        numbers_to_keep, services_to_keep = load_keep_lists('table.tsv')
    except FileNotFoundError:
        print("Error: 'table.tsv' not found. Please ensure it is in the same directory.")
        return

    # Setup CSV Logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_name = f"cleanup_log_{timestamp}.csv"
    
    with open(log_file_name, mode='w', newline='', encoding='utf-8') as log_file:
        log_writer = csv.writer(log_file)
        # Write CSV Headers
        log_writer.writerow(['Account Name', 'Account SID', 'Resource Type', 'Friendly Name / Number', 'Resource SID', 'Action', 'Status', 'Details'])
        
        # Helper function to log to CSV and print to console
        def log_event(acc_name, acc_sid, res_type, name_num, res_sid, action, status, details):
            log_writer.writerow([acc_name, acc_sid, res_type, name_num, res_sid, action, status, details])
            print(f"[{status}] {res_type} {name_num}: {details}")

        print(f"--- Starting Twilio Cleanup (Dry Run: {dry_run}) ---")
        print(f"Loaded {len(numbers_to_keep)} numbers and {len(services_to_keep)} messaging services to KEEP.")
        print(f"Detailed logs will be saved to: {log_file_name}\n")
        
        try:
            print("Fetching all active accounts and subaccounts...")
            accounts = master_client.api.accounts.list(status='active')
        except TwilioRestException as e:
            print(f"Critical Error fetching accounts: {e}")
            return
        
        for account in accounts:
            print(f"\n--- Processing Account: {account.friendly_name} ---")
            sub_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, account.sid)
            # 1. Release unused Twilio numbers
            try:
                phone_numbers = sub_client.incoming_phone_numbers.list()
                
                for number in phone_numbers:
                    if number.phone_number not in numbers_to_keep:
                        if not dry_run:
                            # STEP A: Attempt to remove the emergency address first
                            try:
                                sub_client.incoming_phone_numbers(number.sid).update(
                                    emergency_address_sid=''
                                )
                            except TwilioRestException as update_err:
                                error_msg = str(update_err.msg).lower()
                                if "pending" in error_msg or "unregistration" in error_msg:
                                    log_event(account.friendly_name, account.sid, 'Phone Number', number.phone_number, number.sid, 'Delete', 'PENDING', 'Emergency address unregistration already pending.')
                                    continue # Skip delete and move to the next number
                                else:
                                    log_event(account.friendly_name, account.sid, 'Phone Number', number.phone_number, number.sid, 'Delete', 'ERROR', f"Failed to remove emergency address: {update_err.msg}")
                                    continue # Skip delete and move to the next number
                            
                            # STEP B: Attempt to safely release the number
                            try:
                                sub_client.incoming_phone_numbers(number.sid).delete()
                                log_event(account.friendly_name, account.sid, 'Phone Number', number.phone_number, number.sid, 'Delete', 'SUCCESS', 'Number successfully released')
                            except TwilioRestException as delete_err:
                                error_msg = str(delete_err.msg).lower()
                                if "pending" in error_msg or "unregistration" in error_msg or "emergency address" in error_msg:
                                    log_event(account.friendly_name, account.sid, 'Phone Number', number.phone_number, number.sid, 'Delete', 'PENDING', 'Carrier is processing emergency address removal. Try deleting again later.')
                                else:
                                    log_event(account.friendly_name, account.sid, 'Phone Number', number.phone_number, number.sid, 'Delete', 'ERROR', f"Delete failed: {delete_err.msg}")

                        else:
                            log_event(account.friendly_name, account.sid, 'Phone Number', number.phone_number, number.sid, 'Delete', 'DRY_RUN', 'Would remove emergency address and release number')
                    else:
                        log_event(account.friendly_name, account.sid, 'Phone Number', number.phone_number, number.sid, 'Keep', 'SKIPPED', 'Protected by keep-list')
            except TwilioRestException as e:
                print(f"ERROR fetching numbers for account {account.friendly_name}: {e.msg}")

            # 2. Clean up Messaging Services
            try:
                services = sub_client.messaging.v1.services.list()
                
                for service in services:
                    if service.sid not in services_to_keep:
                        if not dry_run:
                            try:
                                sub_client.messaging.v1.services(service.sid).delete()
                                log_event(account.friendly_name, account.sid, 'Messaging Service', service.friendly_name, service.sid, 'Delete', 'SUCCESS', 'Service successfully deleted')
                            except TwilioRestException as e:
                                log_event(account.friendly_name, account.sid, 'Messaging Service', service.friendly_name, service.sid, 'Delete', 'ERROR', str(e.msg))
                        else:
                            log_event(account.friendly_name, account.sid, 'Messaging Service', service.friendly_name, service.sid, 'Delete', 'DRY_RUN', 'Would delete service')
                    else:
                        log_event(account.friendly_name, account.sid, 'Messaging Service', service.friendly_name, service.sid, 'Keep', 'SKIPPED', 'Protected by keep-list')
            except TwilioRestException as e:
                print(f"ERROR fetching messaging services for account {account.friendly_name}: {e.msg}")

        print(f"\n--- Cleanup Complete. You can review the results in {log_file_name} ---")

if __name__ == "__main__":
    clean_twilio_account(dry_run=True)