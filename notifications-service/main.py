from fastapi import FastAPI
from typing import List
from models import Notification
from aiokafka import AIOKafkaConsumer
from contextlib import asynccontextmanager
import asyncio, json

@asynccontextmanager
async def lifespan(app: FastAPI):
    consumer = AIOKafkaConsumer(
        "order-confirmed",
        "product_not_found_events",
        "out_of_stock_events",
        bootstrap_servers='kafka:9092',
        group_id="notifications-group",
        auto_offset_reset="earliest"
    )
    await consumer.start()
    task = asyncio.create_task(consume(consumer))
    
    yield
    
    task.cancel()
    await consumer.stop()

app = FastAPI(title="Notifications Service", lifespan=lifespan)

notifications_db: List[Notification] = []

async def consume(consumer: AIOKafkaConsumer):
    try:
        async for msg in consumer:
            data = json.loads(msg.value.decode('utf-8'))
            if msg.topic == "order-confirmed":
                notification = Notification(
                    order_id=data['order_id'],
                    product_id=data['product_id'],
                    message=f"Order {data['order_id']} for product {data['product_id']} has been placed."
                )
            elif msg.topic == "product_not_found_events":
                notification = Notification(
                    order_id=data['order_id'],
                    product_id=data['product_id'],
                    message=f"Order {data['order_id']} failed: {data['error_reason']}"
                )
            elif msg.topic == "out_of_stock_events":
                notification = Notification(
                    order_id=data['order_id'],
                    product_id=data['product_id'],
                    message=f"Order {data['order_id']} failed: {data['error_reason']}"
                )
            else:
                continue
            notifications_db.append(notification)
    except asyncio.CancelledError:
        pass

@app.get("/notifications", response_model=List[Notification])
def get_notifications():
    return notifications_db