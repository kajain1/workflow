from dataclasses import dataclass
import uuid
import requests


class InvalidCardError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class NotEnoughBalance(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class CustomerIdNotFound(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class SubmitOrderRetryable(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class Card:
    def __init__(self, card_number: str, balance: float) -> None:
        self.card_number = card_number
        self.balance = balance

class PaymentSystem:
    def __init__(self, cards: list[Card]) -> None:
        self.cards = cards

    def find_card(self, card_number: str) -> Card:
        for card in self.cards:
            if card.card_number == card_number:
                return card
        raise InvalidCardError(f"The card number {card_number} is invalid or doesnt exist in payment system; cant authorize payment")


@dataclass
class TxnProcessingSteps:

    def __init__(self):
        self.mock_payment_api: PaymentSystem = PaymentSystem(
        [
            Card("1212 1212 1212 1212", 2000),
            Card("2323 2323 2323 2323", 0),
        ]
    )

    ##Sync - Request/Response; max 3 retry
    def check_balance(self, card_number:str, amount:float) -> str:
        card = self.mock_payment_api.find_card(card_number)
        if amount > card.balance:
            raise NotEnoughBalance(f"The card {card_number} has insufficient funds to complete this transaction; cant authorize payment")
        else:
            return f"BalanceConfirmationId-{uuid.uuid4()}"


    ##Sync - Request/Response; max 3 retry; passing cart_id+custid as unique identifier for payment processing to not double charge in case of retry
    def process_payment(self,card_number:str, amount:float, cart_id:str, cust_id: str) -> str:
        return f"PaymentConfirmationId-{uuid.uuid4()}"

    ##Sync - Request/Response; max 3 or indefinite retry; if this fails, refund the payment
    def submit_order(self,cart_id:str,store_num:str,product: str) -> str:
        if store_num == "111111":
            raise SubmitOrderRetryable("Order system is down; retrying submit order indefinitely")
        elif store_num == "222222":
            raise Exception("Cant Submit your order; I will refund you now!")
        else:
            return f"TxnId-{uuid.uuid4()}"


    ##Async - If submit_order fails, try catch block of submit_order, indefinite retry; notification if not processed in 3 days
    def refund_payment(self, payment_confirmation_id:str) -> str:
        return f"RefundConfirmationId-FOR-{payment_confirmation_id}"

    ## Post processing; call another workfrom from the activity; only after submit order success
    ##Asyns
    ##retry for 3 hours
    def customer_service(self,cust_id: str) -> str:
        url = f"https://dml8j.wiremockapi.cloud/customers/{cust_id}"
        response = requests.get(url)
        if (response.status_code == 200):
            return response.json()['email_address']
        elif (response.status_code == 404):
            raise CustomerIdNotFound(f"The email for customer_id {cust_id} is not found.")
        else:
            raise Exception(f"Someother Error in customer service")

    #retry for 3 hours max
    def send_email_receipt(self,email_address:str) -> str:
        return f"Sent email to {email_address}."

    ##timer after 30 days
    def send_email_offer(self,email_address:str) -> str:
        return f"Sent email to {email_address} for Offer."
