import random
import sys
import sqlite3
import hashlib

DB_FILE = 'card.s3db'

def init_db():
    """Initializes database table with full schema if it does not exist."""
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
       # Drop table temporarily if migrating from the older structure
        cur.execute("DROP TABLE IF EXISTS card;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS card (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT DEFAULT 'Valued Customer',
                phone TEXT DEFAULT 'N/A',
                number TEXT UNIQUE NOT NULL,
                pin TEXT NOT NULL,
                balance INTEGER DEFAULT 0,
                wallet_balance INTEGER DEFAULT 0
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_card TEXT NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                recipient_name TEXT DEFAULT 'N/A',
                recipient_card TEXT DEFAULT 'N/A',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)    
        conn.commit()


def hash_pin(pin: str) -> str:
    """Hashes the user PIN using SHA-256 for secure storage."""
    return hashlib.sha256(pin.encode()).hexdigest()


class Card:
    def __init__(self):
        self.login_card = ''
        self.login_pin = ''
        self.balance = 0

    # --- LUHN ALGORITHM GENERATOR ---
    def generate_luhn_card(self):
        """Generates a valid 16-digit card number using the Luhn Algorithm."""
        bin_prefix = "400000"
        account_digits = "".join([str(random.randint(0, 9)) for _ in range(9)])
        partial = bin_prefix + account_digits
        
        digits = [int(d) for d in partial]
        for i in range(0, len(digits), 2):
            digits[i] *= 2
            if digits[i] > 9:
                digits[i] -= 9
                
        checksum = (10 - (sum(digits) % 10)) % 10
        return partial + str(checksum)

    def is_valid_luhn(self, card_number: str) -> bool:
        """Validates whether a card number satisfies the Luhn check."""
        if not card_number.isdigit() or len(card_number) != 16:
            return False
        
        digits = [int(d) for d in card_number]
        checksum = digits.pop()
        
        for i in range(0, len(digits), 2):
            digits[i] *= 2
            if digits[i] > 9:
                digits[i] -= 9
                
        total = sum(digits) + checksum
        return total % 10 == 0

    # --- ACCOUNT CREATION ---
    def create_account(self):
        print("\n--- CREATE AN ACCOUNT ---")
        name = input("Enter Full Name: ").strip()
        phone = input("Enter Phone Number: ").strip()
        
        while True:
            pin = input("Create a 4-digit PIN: ").strip()
            if len(pin) == 4 and pin.isdigit():
                break
            print("Invalid PIN! Must be exactly 4 digits.")

        while True:
            try:
                initial_deposit = int(input("Initial Deposit ($): ").strip())
                if initial_deposit >= 0:
                    break
                print("Deposit amount cannot be negative.")
            except ValueError:
                print("Please enter a valid numeric amount.")

        card_number = self.generate_luhn_card()
        hashed_pin = hash_pin(pin)

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO card (name, phone, number, pin, balance) VALUES (?, ?, ?, ?, ?);",
                (name, phone, card_number, hashed_pin, initial_deposit)
            )
            conn.commit()

        print("\nYour card has been created!")
        print(f"Account Holder: {name}")
        print(f"Your Card Number: {card_number}")
        print(f"Your Card PIN:    {pin} (Securely encrypted in DB)")
        print(f"Starting Balance: ${initial_deposit}")

    # --- LOGIN SYSTEM ---
    def create_account(self):
        print("\n--- CREATE ACCOUNT ---")
        name = input("Enter full name: ").strip()
        phone = input("Enter phone number: ").strip()
        
        while True:
            try:
                initial_deposit = int(input("Enter initial deposit ($): ").strip())
                if initial_deposit >= 0:
                    break
                print("Deposit amount cannot be negative.")
            except ValueError:
                print("Please enter a valid number.")

        card_number = self.generate_luhn_card()
        pin = f"{random.randint(0, 9999):04d}"
        hashed_pin = hash_pin(pin)

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO card (name, phone, number, pin, balance, wallet_balance) 
                   VALUES (?, ?, ?, ?, ?, 0);""",
                (name, phone, card_number, hashed_pin, initial_deposit)
            )
            conn.commit()

        print("\nYour card has been created")
        print(f"Your card number:\n{card_number}")
        print(f"Your card PIN:\n{pin}")

    def login(self):
        print("\n--- LOG IN ---")
        card_num = input("Enter your card number:\n").strip()
        pin_input = input("Enter your PIN:\n").strip()
        hashed_pin_input = hash_pin(pin_input)

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT name, balance FROM card WHERE number = ? AND pin = ?;",
                (card_num, hashed_pin_input)
            )
            row = cur.fetchone()

        if row:
            account_holder, self.balance = row[0], row[1]
            self.login_card = card_num
            print(f"\nWelcome back, {account_holder}! You have successfully logged in.")
            self.success()
        else:
            print("\nWrong card number or PIN!")   
             
    def bank_to_wallet(self):
        print("\n--- BANK TO WALLET TRANSFER ---")
        try:
            amount = int(input("Enter amount to transfer to wallet ($): ").strip())
            if amount <= 0:
                print("Amount must be greater than 0.")
                return

            # Calculate 2% transaction tax
            tax = amount * 0.02
            total_deduction = amount + tax

            with sqlite3.connect(DB_FILE) as conn:
                cur = conn.cursor()
                cur.execute("SELECT balance, wallet_balance FROM card WHERE number = ?;", (self.login_card,))
                bank_bal, wallet_bal = cur.fetchone()

                if total_deduction > bank_bal:
                    print(f"Insufficient bank balance! You need ${total_deduction:.2f} (Amount: ${amount} + 2% Tax: ${tax:.2f}).")
                else:
                    new_bank_bal = bank_bal - total_deduction
                    new_wallet_bal = wallet_bal + amount

                    cur.execute(
                        "UPDATE card SET balance = ?, wallet_balance = ? WHERE number = ?;",
                        (new_bank_bal, new_wallet_bal, self.login_card)
                    )
                    conn.commit()

                    self.log_transaction(
                        tx_type="Bank to Mobile Wallet", 
                        amount=amount, 
                        recipient_name="Self (Mobile Wallet)", 
                        recipient_card=self.login_card
                    )

                    print(f"\nSuccessfully transferred ${amount} from Bank to Mobile Wallet!")
                    print(f"Transaction Tax (2%): ${tax:.2f}")
                    print(f"Total Deducted from Bank: ${total_deduction:.2f}")
                    print(f"New Bank Balance:   ${new_bank_bal:.2f}")
                    print(f"New Wallet Balance: ${new_wallet_bal:.2f}")
        except ValueError:
            print("Invalid input amount.")

    def wallet_to_bank(self):
        print("\n--- WALLET TO BANK TRANSFER ---")
        try:
            amount = int(input("Enter amount to transfer to bank ($): ").strip())
            if amount <= 0:
                print("Amount must be greater than 0.")
                return

            with sqlite3.connect(DB_FILE) as conn:
                cur = conn.cursor()
                cur.execute("SELECT balance, wallet_balance FROM card WHERE number = ?;", (self.login_card,))
                bank_bal, wallet_bal = cur.fetchone()

                if amount > wallet_bal:
                    print("Insufficient wallet balance!")
                else:
                    cur.execute(
                        "UPDATE card SET balance = balance + ?, wallet_balance = wallet_balance - ? WHERE number = ?;",
                        (amount, amount, self.login_card)
                    )
                    conn.commit()

                    self.log_transaction(
                        tx_type="Mobile Wallet to Bank",
                        amount=amount,
                        recipient_name="Self (Bank Account)",
                        recipient_card=self.login_card
                    )

                    print(f"\nSuccessfully transferred ${amount} from Mobile Wallet to Bank!")
                    print(f"New Bank Balance:   ${bank_bal + amount}")
                    print(f"New Wallet Balance: ${wallet_bal - amount}")
        except ValueError:
            print("Invalid input amount.")

    def log_transaction(self, tx_type, amount, recipient_name="N/A", recipient_card="N/A"):
        """Logs transaction details into the transactions database table."""
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO transactions (sender_card, type, amount, recipient_name, recipient_card) 
                   VALUES (?, ?, ?, ?, ?);""",
                (self.login_card, tx_type, amount, recipient_name, recipient_card)
            )
            conn.commit()

    def view_recent_activities(self):
        """Displays the logged transaction history with date and time."""
        print("\n--- RECENT ACTIVITIES / TRANSACTION HISTORY ---")
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT type, amount, recipient_name, recipient_card, timestamp 
                   FROM transactions 
                   WHERE sender_card = ? 
                   ORDER BY timestamp DESC LIMIT 10;""",
                (self.login_card,)
            )
            rows = cur.fetchall()

        if not rows:
            print("No recent activities found.")
            return

        print(f"{'Date & Time':<20} | {'Type':<22} | {'Amount ($)':<10} | {'Recipient Name':<20} | {'Recipient Card'}")
        print("-" * 90)
        for row in rows:
            tx_type, amount, r_name, r_card, timestamp = row
            print(f"{timestamp:<20} | {tx_type:<22} | ${amount:<9.2f} | {r_name:<20} | {r_card}")

    # --- USER DASHBOARD ---
    def success(self):        
        while True:
            print("""\n--- USER MENU ---
1. Balance
2. Add income
3. Do transfer
4. Bank to Mobile Wallet
5. Mobile Wallet to Bank
6. Recent activities
7. Close account
8. Log out
9. Exit""")
            try:
                choice = int(input("Select an option: ").strip())
            except ValueError:
                print("Invalid selection. Enter a number.")
                continue

            if choice == 1:
                # Refresh balance from database
                with sqlite3.connect(DB_FILE) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT balance FROM card WHERE number = ?;", (self.login_card,))
                    self.balance = cur.fetchone()[0]
                print(f"\nBalance: ${self.balance}")

            elif choice == 2:
                try:
                    amount = int(input("\nEnter income:\n").strip())
                    if amount <= 0:
                        print("Amount must be positive.")
                        continue
                        
                    with sqlite3.connect(DB_FILE) as conn:
                        cur = conn.cursor()
                        cur.execute(
                            "UPDATE card SET balance = balance + ? WHERE number = ?;",
                            (amount, self.login_card)
                        )
                        conn.commit()
                    print("Income was added!")
                except ValueError:
                    print("Invalid amount input.")

            elif choice == 3:
                print("\n--- MONEY TRANSFER ---")
                receiver_card = input("Enter receiver card number:\n").strip()

                if receiver_card == self.login_card:
                    print("You can't transfer money to yourself!")
                    continue

                if not self.is_valid_luhn(receiver_card):
                    print("Probably you made a mistake in the card number. Please try again!")
                    continue

                with sqlite3.connect(DB_FILE) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT balance FROM card WHERE number = ?;", (receiver_card,))
                    receiver_row = cur.fetchone()

                if not receiver_row:
                    print("Such a card does not exist.")
                else:
                    try:
                        transfer = int(input("Enter how much money you want to transfer:\n").strip())
                        
                        # Refresh sender balance check
                        with sqlite3.connect(DB_FILE) as conn:
                            cur = conn.cursor()
                            cur.execute("SELECT balance FROM card WHERE number = ?;", (self.login_card,))
                            self.balance = cur.fetchone()[0]

                        if transfer > self.balance:
                            print("Not enough money!")
                        elif transfer <= 0:
                            print("Transfer amount must be positive.")
                        else:
                            # Perform atomic transfer transaction
                            with sqlite3.connect(DB_FILE) as conn:
                                cur = conn.cursor()
                                # Deduct from sender
                                cur.execute(
                                    "UPDATE card SET balance = balance - ? WHERE number = ?;",
                                    (transfer, self.login_card)
                                )
                                # Add to recipient
                                cur.execute(
                                    "UPDATE card SET balance = balance + ? WHERE number = ?;",
                                    (transfer, receiver_card)
                                )
                                conn.commit()

                                self.log_transaction(
                                tx_type="Bank-to-Bank Transfer", 
                                amount=transfer, 
                                recipient_name=receiver_row[0] if len(receiver_row) > 1 else "External Account", 
                                recipient_card=receiver_card

                                )

                            print("Success!")
                    except ValueError:
                        print("Invalid transfer amount.")

            elif choice == 4:
                self.bank_to_wallet()  

            elif choice == 5:
                self.wallet_to_bank()

            elif choice == 6:
                self.view_recent_activities()    

            elif choice == 7:
                with sqlite3.connect(DB_FILE) as conn:
                    cur = conn.cursor()
                    cur.execute("DELETE FROM card WHERE number = ?;", (self.login_card,))
                    conn.commit()
                print("\nThe account has been closed!")
                break

            elif choice == 7:
                print("\nYou have successfully logged out!")
                break

            elif choice == 0:
                print("\nBye!")
                sys.exit()

    # --- MAIN MENU ---
    def menu(self):
        init_db()
        while True:
            print("""\n--- MAIN MENU ---
1. Create an account
2. Log into account
3. Exit""")
            try:
                choice = int(input("Select option: ").strip())
            except ValueError:
                print("Invalid input! Please enter a number.")
                continue

            if choice == 1:
                self.create_account()
            elif choice == 2:
                self.login()
            elif choice == 0:
                print("\nBye!")
                break
            else:
                print("Invalid choice. Try again.")


if __name__ == "__main__":
    card_app = Card()
    card_app.menu()
