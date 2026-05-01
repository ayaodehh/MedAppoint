from decimal import Decimal
from uuid import uuid4


def process_payment_stub(invoice, amount: Decimal):
    return {
        "accepted": True,
        "gateway_reference": f"stub-pay-{uuid4()}",
        "invoice_id": invoice.pk,
        "amount": str(amount),
        "message": "Stubbed payment accepted. No real network call was made.",
    }
