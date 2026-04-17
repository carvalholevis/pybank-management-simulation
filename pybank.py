import textwrap
from abc import ABC, abstractclassmethod, abstractproperty
from datetime import datetime


class AccountsIterator:
    def __init__(self, accounts):
        self.accounts = accounts
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        try:
            account = self.accounts[self._index]
            return f"""\
            Branch:\t\t{account.branch}
            Number:\t\t{account.number}
            Holder:\t\t{account.customer.name}
            Balance:\t$ {account.balance:.2f}
        """
        except IndexError:
            raise StopIteration
        finally:
            self._index += 1


class Customer:
    def __init__(self, address):
        self.address = address
        self.accounts = []
        self.account_index = 0

    def perform_transaction(self, account, transaction):
        if len(account.history.daily_transactions()) >= 2:
            print("\n@@@ You have exceeded the number of allowed transactions for today! @@@")
            return

        transaction.register(account)

    def add_account(self, account):
        self.accounts.append(account)


class Individual(Customer):
    def __init__(self, name, birth_date, cpf, address):
        super().__init__(address)
        self.name = name
        self.birth_date = birth_date
        self.cpf = cpf


class Account:
    def __init__(self, number, customer):
        self._balance = 0
        self._number = number
        self._branch = "0001"
        self._customer = customer
        self._history = History()

    @classmethod
    def new_account(cls, customer, number):
        return cls(number, customer)

    @property
    def balance(self):
        return self._balance

    @property
    def number(self):
        return self._number

    @property
    def branch(self):
        return self._branch

    @property
    def customer(self):
        return self._customer

    @property
    def history(self):
        return self._history

    def withdraw(self, amount):
        balance = self.balance
        exceeded_balance = amount > balance

        if exceeded_balance:
            print("\n@@@ Operation failed! You don't have enough balance. @@@")

        elif amount > 0:
            self._balance -= amount
            print("\n=== Withdrawal successful! ===")
            return True

        else:
            print("\n@@@ Operation failed! The provided amount is invalid. @@@")

        return False

    def deposit(self, amount):
        if amount > 0:
            self._balance += amount
            print("\n=== Deposit successful! ===")
        else:
            print("\n@@@ Operation failed! The provided amount is invalid. @@@")
            return False

        return True


class CheckingAccount(Account):
    def __init__(self, number, customer, limit=500, withdrawal_limit=3):
        super().__init__(number, customer)
        self._limit = limit
        self._withdrawal_limit = withdrawal_limit

    @classmethod
    def new_account(cls, customer, number, limit, withdrawal_limit):
        return cls(number, customer, limit, withdrawal_limit)

    def withdraw(self, amount):
        number_of_withdrawals = len(
            [
                transaction
                for transaction in self.history.transactions
                if transaction["type"] == Withdrawal.__name__
            ]
        )

        exceeded_limit = amount > self._limit
        exceeded_withdrawals = number_of_withdrawals >= self._withdrawal_limit

        if exceeded_limit:
            print("\n@@@ Operation failed! The withdrawal amount exceeds the limit. @@@")

        elif exceeded_withdrawals:
            print("\n@@@ Operation failed! Maximum number of withdrawals exceeded. @@@")

        else:
            return super().withdraw(amount)

        return False

    def __str__(self):
        return f"""\
            Branch:\t\t{self.branch}
            C/A:\t\t{self.number}
            Holder:\t\t{self.customer.name}
        """


class History:
    def __init__(self):
        self._transactions = []

    @property
    def transactions(self):
        return self._transactions

    def add_transaction(self, transaction):
        self._transactions.append(
            {
                "type": transaction.__class__.__name__,
                "amount": transaction.amount,
                "date": datetime.utcnow().strftime("%d-%m-%Y %H:%M:%S"),
            }
        )

    def generate_report(self, transaction_type=None):
        for transaction in self._transactions:
            if (
                transaction_type is None
                or transaction["type"].lower() == transaction_type.lower()
            ):
                yield transaction

    def daily_transactions(self):
        current_date = datetime.utcnow().date()
        transactions = []
        for transaction in self._transactions:
            transaction_date = datetime.strptime(
                transaction["date"], "%d-%m-%Y %H:%M:%S"
            ).date()
            if current_date == transaction_date:
                transactions.append(transaction)
        return transactions


class Transaction(ABC):
    @property
    @abstractproperty
    def amount(self):
        pass

    @abstractclassmethod
    def register(self, account):
        pass


class Withdrawal(Transaction):
    def __init__(self, amount):
        self._amount = amount

    @property
    def amount(self):
        return self._amount

    def register(self, account):
        transaction_success = account.withdraw(self.amount)

        if transaction_success:
            account.history.add_transaction(self)


class Deposit(Transaction):
    def __init__(self, amount):
        self._amount = amount

    @property
    def amount(self):
        return self._amount

    def register(self, account):
        transaction_success = account.deposit(self.amount)

        if transaction_success:
            account.history.add_transaction(self)


def log_transaction(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        print(f"{datetime.now()}: {func.__name__.upper()}")
        return result

    return wrapper


def show_menu():
    menu = """\n
    ================ MENU ================
    [d]\tDeposit
    [w]\tWithdraw
    [s]\tStatement
    [na]\tNew account
    [la]\tList accounts
    [nu]\tNew user
    [q]\tQuit
    => """
    return input(textwrap.dedent(menu))


def filter_customer(cpf, customers):
    filtered_customers = [customer for customer in customers if customer.cpf == cpf]
    return filtered_customers[0] if filtered_customers else None


def retrieve_customer_account(customer):
    if not customer.accounts:
        print("\n@@@ Customer has no account! @@@")
        return

    # FIXME: does not allow customer to choose the account
    return customer.accounts[0]


@log_transaction
def deposit_funds(customers):
    cpf = input("Enter the customer's CPF: ")
    customer = filter_customer(cpf, customers)

    if not customer:
        print("\n@@@ Customer not found! @@@")
        return

    amount = float(input("Enter the deposit amount: "))
    transaction = Deposit(amount)

    account = retrieve_customer_account(customer)
    if not account:
        return

    customer.perform_transaction(account, transaction)


@log_transaction
def withdraw_funds(customers):
    cpf = input("Enter the customer's CPF: ")
    customer = filter_customer(cpf, customers)

    if not customer:
        print("\n@@@ Customer not found! @@@")
        return

    amount = float(input("Enter the withdrawal amount: "))
    transaction = Withdrawal(amount)

    account = retrieve_customer_account(customer)
    if not account:
        return

    customer.perform_transaction(account, transaction)


@log_transaction
def display_statement(customers):
    cpf = input("Enter the customer's CPF: ")
    customer = filter_customer(cpf, customers)

    if not customer:
        print("\n@@@ Customer not found! @@@")
        return

    account = retrieve_customer_account(customer)
    if not account:
        return

    print("\n================ STATEMENT ================")
    statement = ""
    has_transaction = False
    for transaction in account.history.generate_report():
        has_transaction = True
        statement += f"\n{transaction['date']}\n{transaction['type']}:\n\t$ {transaction['amount']:.2f}"

    if not has_transaction:
        statement = "No movements were made"

    print(statement)
    print(f"\nBalance:\n\t$ {account.balance:.2f}")
    print("===========================================")


@log_transaction
def create_customer(customers):
    cpf = input("Enter the CPF (numbers only): ")
    customer = filter_customer(cpf, customers)

    if customer:
        print("\n@@@ A customer with this CPF already exists! @@@")
        return

    name = input("Enter the full name: ")
    birth_date = input("Enter the birth date (dd-mm-yyyy): ")
    address = input(
        "Enter the address (street, number - neighborhood - city/state abbreviation): "
    )

    customer = Individual(
        name=name, birth_date=birth_date, cpf=cpf, address=address
    )

    customers.append(customer)

    print("\n=== Customer created successfully! ===")


@log_transaction
def create_account(account_number, customers, accounts):
    cpf = input("Enter the customer's CPF: ")
    customer = filter_customer(cpf, customers)

    if not customer:
        print("\n@@@ Customer not found, account creation flow terminated! @@@")
        return

    account = CheckingAccount.new_account(
        customer=customer, number=account_number, limit=500, withdrawal_limit=50
    )
    accounts.append(account)
    customer.accounts.append(account)

    print("\n=== Account created successfully! ===")


def list_accounts(accounts):
    for account in AccountsIterator(accounts):
        print("=" * 100)
        print(textwrap.dedent(str(account)))


def main():
    customers = []
    accounts = []

    while True:
        option = show_menu()

        if option == "d":
            deposit_funds(customers)

        elif option == "w":
            withdraw_funds(customers)

        elif option == "s":
            display_statement(customers)

        elif option == "nu":
            create_customer(customers)

        elif option == "na":
            account_number = len(accounts) + 1
            create_account(account_number, customers, accounts)

        elif option == "la":
            list_accounts(accounts)

        elif option == "q":
            break

        else:
            print(
                "\n@@@ Invalid operation, please select the desired operation again. @@@"
            )

if __name__ == "__main__":
    main()