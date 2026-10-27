from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal, InvalidOperation


class Transaction:
    """Represents one transaction in an account's history."""

    def __init__(self, transaction_type, amount, balance_after, note=""):
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.transaction_type = transaction_type
        self.amount = Decimal(str(amount)).quantize(Decimal("0.01"))
        self.balance_after = Decimal(str(balance_after)).quantize(Decimal("0.01"))
        self.note = note

    def __str__(self):
        note = f" | {self.note}" if self.note else ""
        return (
            f"{self.timestamp} | {self.transaction_type:<12} | "
            f"Amount: ₹{self.amount:.2f} | Balance: ₹{self.balance_after:.2f}{note}"
        )


class Account(ABC):
    """Abstract base class shared by all account types."""

    def __init__(self, account_number, holder_name, opening_balance=0):
        if not str(account_number).strip():
            raise ValueError("Account number cannot be empty.")
        if not str(holder_name).strip():
            raise ValueError("Account holder name cannot be empty.")

        self.account_number = str(account_number).strip()
        self.holder_name = str(holder_name).strip()
        self.__balance = self._money(opening_balance, allow_zero=True)
        self._transactions = []

        if self.__balance > 0:
            self._record("OPENING", self.__balance, "Opening balance")

    @staticmethod
    def _money(value, allow_zero=False):
        try:
            amount = Decimal(str(value)).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            raise ValueError("Enter a valid numeric amount.") from None
        if not amount.is_finite() or amount < 0 or (not allow_zero and amount == 0):
            raise ValueError("Amount must be positive." if not allow_zero else
                             "Amount cannot be negative.")
        return amount

    @property
    def balance(self):
        """Read-only balance property (encapsulation)."""
        return self.__balance

    @abstractmethod
    def withdraw(self, amount):
        """Withdraw funds according to the account's rules."""

    @abstractmethod
    def account_type(self):
        """Return the account type name."""

    def deposit(self, amount):
        amount = self._money(amount)
        self.__balance += amount
        self._record("DEPOSIT", amount)
        return self.__balance

    def _deduct(self, amount, transaction_type="WITHDRAW", note=""):
        amount = self._money(amount)
        self.__balance -= amount
        self._record(transaction_type, amount, note)
        return self.__balance

    def _record(self, transaction_type, amount, note=""):
        self._transactions.append(
            Transaction(transaction_type, amount, self.__balance, note)
        )

    def transaction_history(self):
        return list(self._transactions)

    def show_details(self):
        return (
            f"Account number: {self.account_number}\n"
            f"Holder name: {self.holder_name}\n"
            f"Account type: {self.account_type()}\n"
            f"Balance: ₹{self.balance:.2f}"
        )


class SavingsAccount(Account):
    """Savings account does not allow spending beyond the balance."""

    def withdraw(self, amount):
        amount = self._money(amount)
        if amount > self.balance:
            raise ValueError("Insufficient balance.")
        return self._deduct(amount)

    def account_type(self):
        return "Savings"


class CurrentAccount(Account):
    """Current account may use its configured overdraft limit."""

    def __init__(self, account_number, holder_name, opening_balance=0,
                 overdraft_limit=5000):
        super().__init__(account_number, holder_name, opening_balance)
        self.overdraft_limit = self._money(overdraft_limit, allow_zero=True)

    def withdraw(self, amount):
        amount = self._money(amount)
        if amount > self.balance + self.overdraft_limit:
            raise ValueError("Withdrawal exceeds the overdraft limit.")
        return self._deduct(amount)

    def account_type(self):
        return "Current"


class Bank:
    """Creates accounts and coordinates transfers between them."""

    def __init__(self, name="Python Community Bank"):
        self.name = name
        self._accounts = {}

    def create_account(self, kind, account_number, holder_name, opening_balance=0,
                       overdraft_limit=5000):
        number = str(account_number).strip()
        if number in self._accounts:
            raise ValueError("This account number already exists.")

        if kind.lower() == "savings":
            account = SavingsAccount(number, holder_name, opening_balance)
        elif kind.lower() == "current":
            account = CurrentAccount(
                number, holder_name, opening_balance, overdraft_limit
            )
        else:
            raise ValueError("Choose 'savings' or 'current'.")

        self._accounts[number] = account
        return account

    def get_account(self, account_number):
        account = self._accounts.get(str(account_number).strip())
        if account is None:
            raise ValueError("Account not found.")
        return account

    def all_accounts(self):
        return list(self._accounts.values())

    def transfer(self, from_number, to_number, amount):
        if str(from_number).strip() == str(to_number).strip():
            raise ValueError("Choose two different accounts.")

        source = self.get_account(from_number)
        destination = self.get_account(to_number)
        value = Account._money(amount)

        # Check the source account's withdrawal rules before changing balances.
        if isinstance(source, SavingsAccount) and value > source.balance:
            raise ValueError("Insufficient balance.")
        if isinstance(source, CurrentAccount) and value > source.balance + source.overdraft_limit:
            raise ValueError("Withdrawal exceeds the overdraft limit.")

        source._deduct(value, "TRANSFER OUT", f"To {destination.account_number}")
        destination.deposit(value)
        destination._record("TRANSFER IN", value, f"From {source.account_number}")
        return True


def read_amount(prompt, allow_zero=False):
    raw = input(prompt).strip()
    try:
        amount = Decimal(raw).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise ValueError("Please enter a valid number.") from None
    if not amount.is_finite() or amount < 0 or (not allow_zero and amount == 0):
        raise ValueError("Enter a positive amount.")
    return amount


def main():
    bank = Bank()
    print(f"Welcome to {bank.name}!")

    while True:
        print(
            "\n--- BANKING SYSTEM ---\n"
            "1. Create account\n"
            "2. View account details\n"
            "3. Deposit money\n"
            "4. Withdraw money\n"
            "5. Transaction history\n"
            "6. Transfer money\n"
            "7. List all accounts\n"
            "0. Exit"
        )
        choice = input("Choose an option: ").strip()

        try:
            if choice == "0":
                print("Thank you for using the banking system!")
                break
            if choice == "1":
                kind = input("Account type (savings/current): ").strip().lower()
                number = input("Account number: ").strip()
                name = input("Account holder name: ").strip()
                opening = read_amount("Opening balance (0 if none): ", allow_zero=True)
                limit = 0
                if kind == "current":
                    limit = read_amount("Overdraft limit (0 if none): ", allow_zero=True)
                account = bank.create_account(kind, number, name, opening, limit)
                print("Account created successfully!\n" + account.show_details())
            elif choice == "2":
                print(bank.get_account(input("Account number: ")).show_details())
            elif choice == "3":
                account = bank.get_account(input("Account number: "))
                account.deposit(read_amount("Deposit amount: "))
                print(f"Deposit successful. Balance: ₹{account.balance:.2f}")
            elif choice == "4":
                account = bank.get_account(input("Account number: "))
                account.withdraw(read_amount("Withdrawal amount: "))
                print(f"Withdrawal successful. Balance: ₹{account.balance:.2f}")
            elif choice == "5":
                account = bank.get_account(input("Account number: "))
                history = account.transaction_history()
                if not history:
                    print("No transactions yet.")
                else:
                    for transaction in history:
                        print(transaction)
            elif choice == "6":
                source = input("From account number: ")
                destination = input("To account number: ")
                amount = read_amount("Transfer amount: ")
                bank.transfer(source, destination, amount)
                print("Transfer successful.")
            elif choice == "7":
                accounts = bank.all_accounts()
                if not accounts:
                    print("No accounts have been created.")
                for account in accounts:
                    print("-" * 35)
                    print(account.show_details())
            else:
                print("Invalid option. Please choose from the menu.")
        except ValueError as error:
            print(f"Error: {error}")


if __name__ == "__main__":
    main()
