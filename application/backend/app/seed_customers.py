"""Seed customer accounts and sentiment records linked to fiber nodes."""
import logging
import random
from sqlalchemy.orm import Session
from sqlalchemy import func

from .models import FiberNodeModel, CustomerAccountModel, CustomerSentimentModel
from .generator import generate_customer_account, generate_customer_sentiment

logger = logging.getLogger(__name__)


def seed_customers(db: Session) -> int:
    """
    Seed customer accounts and sentiment if the customer_accounts table is empty.
    Generates 2-4 customers per node (proportional to homes_active).
    Returns the count of customers created.
    """
    existing = db.query(func.count(CustomerAccountModel.id)).scalar()
    if existing > 0:
        return 0

    nodes = db.query(
        FiberNodeModel.node_id,
        FiberNodeModel.city,
        FiberNodeModel.state,
        FiberNodeModel.homes_active,
    ).all()

    if not nodes:
        logger.warning("No fiber nodes found - skipping customer seeding")
        return 0

    logger.info("Seeding customer accounts...")

    customers = []
    sentiments = []
    acct_idx = 1
    sent_idx = 1

    for node_id, city, state, homes_active in nodes:
        # Scale customers proportional to homes_active (2-4 per node, capped)
        homes = homes_active or 100
        num_customers = max(2, min(4, homes // 200))

        for _ in range(num_customers):
            cust = generate_customer_account(acct_idx, node_id, city or "", state or "")
            cust["id"] = acct_idx
            customers.append(cust)

            # Generate 1-3 sentiment records per customer
            num_sentiments = random.randint(1, 3)
            for _ in range(num_sentiments):
                sent = generate_customer_sentiment(cust["account_id"])
                sent["id"] = sent_idx
                sentiments.append(sent)
                sent_idx += 1

            acct_idx += 1

            # Batch insert every 5000 customers to avoid memory pressure
            if len(customers) >= 5000:
                db.bulk_insert_mappings(CustomerAccountModel, customers)
                db.bulk_insert_mappings(CustomerSentimentModel, sentiments)
                db.flush()
                customers.clear()
                sentiments.clear()

    # Insert remaining
    if customers:
        db.bulk_insert_mappings(CustomerAccountModel, customers)
    if sentiments:
        db.bulk_insert_mappings(CustomerSentimentModel, sentiments)

    db.commit()
    total = acct_idx - 1
    logger.info(f"Seeded {total} customer accounts and {sent_idx - 1} sentiment records")
    return total
