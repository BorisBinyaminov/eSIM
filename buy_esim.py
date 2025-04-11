"""
Refactored buy_esim.py

This module interacts with the ESIMAccess API using asynchronous HTTP calls via aiohttp.
It handles processes such as balance checking, order placement, profile querying (including polling),
and related operations (e.g. top-up and cancellation).

All database operations use context managers for safe session management.
"""

import os
import asyncio
import uuid
import logging
import json
import aiohttp
from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session
from database import SessionLocal
from models import Order

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Global constants for the ESIMAccess API
BASE_URL = "https://api.esimaccess.com/api/v1/open"
API_HEADERS = {
    "RT-AccessCode": os.getenv("REACT_APP_ESIM_API_Access_Code"),
    "RT-SecretKey": os.getenv("REACT_APP_ESIM_API_Secret_KEY"),
    "Content-Type": "application/json"
}


async def api_post(url: str, payload: dict, timeout: int = 30, retries: int = 3, backoff_factor: float = 1.0) -> dict:
    """
    Helper function to send POST requests to the API asynchronously using aiohttp.
    Implements a simple retry mechanism with exponential backoff.
    """
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=API_HEADERS, timeout=timeout) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data
        except Exception as e:
            logger.warning(f"[API POST] Attempt {attempt+1} for URL {url} failed: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(backoff_factor * (2 ** attempt))
            else:
                logger.error(f"[API POST] All attempts failed for URL {url}")
                raise


# -----------------------------
# 0. User Payment Simulation
# -----------------------------
def user_payment_sync() -> str:
    """
    Simulate user payment approval.
    In production, integrate with an actual payment gateway.
    """
    return str(uuid.uuid4())


async def user_payment() -> str:
    return await asyncio.to_thread(user_payment_sync)


# -----------------------------
# 1. Check Balance
# -----------------------------
async def check_balance() -> dict:
    """
    Check account balance from the ESIMAccess API.
    """
    url = f"{BASE_URL}/balance/query"
    return await api_post(url, payload={}, timeout=30)


# -----------------------------
# 2. Place Order
# -----------------------------
async def place_order(
    package_code: str, 
    order_price: int, 
    transaction_id: str, 
    period_num: Optional[int] = None, 
    count: int = 1
) -> dict:
    """
    Place an eSIM order. For daily plans, `period_num` is provided.
    """
    url = f"{BASE_URL}/esim/order"
    if period_num:  # daily plan
        final_count = 1
        total_amount = order_price * period_num
    else:
        final_count = count
        total_amount = order_price * count

    payload = {
        "transactionId": transaction_id,
        "amount": total_amount,
        "packageInfoList": [{
            "packageCode": package_code,
            "count": final_count,
            "price": order_price
        }]
    }
    if period_num:
        payload["packageInfoList"][0]["periodNum"] = period_num

    return await api_post(url, payload, timeout=30)


# -----------------------------
# 3. Query Profile (Retrieve QR Code/Profile)
# -----------------------------
async def query_profile(order_no: str) -> dict:
    """
    Query the ESIMAccess API for allocated eSIM profiles associated with an order.
    """
    url = f"{BASE_URL}/esim/query"
    payload = {"orderNo": order_no, "pager": {"pageNum": 1, "pageSize": 20}}
    return await api_post(url, payload, timeout=60)


async def poll_profile(order_no: str, timeout: int = 30, interval: int = 5) -> dict:
    logger.info(f"⏳ Polling for profile allocation (order {order_no})...")
    start_time = asyncio.get_event_loop().time()
    while True:
        query_response = await query_profile(order_no)
        if not isinstance(query_response, dict):
            logger.warning(f"Unexpected response type ({type(query_response)}) for order {order_no}. Using empty dict.")
            query_response = {}

        obj_data = query_response.get("obj")
        esim_list_raw = []  # default

        # Handle the case where 'obj' is a dict
        if isinstance(obj_data, dict):
            esim_list_raw = obj_data.get("esimList", [])

        # Or where 'obj' is a list
        elif isinstance(obj_data, list):
            # E.g. if each item might contain an 'esimList'
            for item in obj_data:
                if isinstance(item, dict) and "esimList" in item:
                    esim_list_raw.extend(item["esimList"])

        if esim_list_raw:
            logger.info(f"✅ QR profiles allocated: {len(esim_list_raw)}")
            return query_response
        else:
            logger.info("⚠️ Polling result: No profiles allocated yet.")

        if asyncio.get_event_loop().time() - start_time > timeout:
            logger.error("❌ Timeout reached while waiting for profile allocation.")
            break

        await asyncio.sleep(interval)

    raise Exception("Timeout: eSIM profiles are still being allocated. Please try again later.")


# -----------------------------
# 4. Process Purchase
# -----------------------------
async def process_purchase(
    package_code: str, 
    user_id: str, 
    order_price: int, 
    retail_price: int, 
    count: int = 1, 
    period_num: Optional[int] = None
) -> dict:
    """
    Process the purchase flow:
      - Check balance
      - Simulate payment
      - Place order and poll for profile allocation
      - Save order data in the database
    """
    balance_data = await check_balance()
    available_balance = balance_data.get("obj", {}).get("balance", 0)
    if available_balance < order_price * count:
        logger.error(f"Insufficient funds: available {available_balance}, required {order_price * count}")
        raise Exception("Insufficient funds to place the order.")

    transaction_id = await user_payment()
    logger.info(f"Simulated transaction ID: {transaction_id}")

    order_response = await place_order(package_code, order_price, transaction_id, period_num=period_num, count=count)
    if not order_response or not isinstance(order_response, dict):
        raise Exception("Order request failed or returned unexpected result.")
    logger.info(f"Order response: {order_response}")
    if not order_response.get("success"):
        raise Exception(f"Order failed: {order_response.get('errorMsg')}")
    order_no = order_response.get("obj", {}).get("orderNo")
    if not order_no:
        raise Exception("Order API did not return an orderNo.")

    query_response = await poll_profile(order_no, timeout=30, interval=5)
    if not query_response or not isinstance(query_response, dict):
        raise Exception("Polling failed: no profile response received.")

    esim_list_raw = query_response.get("obj", {}).get("esimList", [])
    if not esim_list_raw:
        raise Exception("No eSIM profile returned.")

    qr_codes = [profile.get("qrCodeUrl") for profile in esim_list_raw if profile.get("qrCodeUrl")]
    if not qr_codes:
        raise Exception("No QR codes found in the response.")

    orders_created = []
    # Use a context manager for DB session to ensure safe commit/rollback.
    with SessionLocal() as session:
        for profile in esim_list_raw:
            iccid_value = profile.get("iccid")
            qr_code = profile.get("qrCodeUrl")
            if not iccid_value or not qr_code:
                continue

            new_order = Order(
                user_id=user_id,
                package_code=package_code,
                order_id=order_no,
                transaction_id=transaction_id,
                iccid=iccid_value,
                count=1,
                period_num=period_num,
                price=order_price,
                retail_price=retail_price,
                qr_code=qr_code,
                status="confirmed",
                details=None,
                esim_status=profile.get("esimStatus"),
                smdp_status=profile.get("smdpStatus"),
                expired_time=profile.get("expiredTime"),
                total_volume=profile.get("totalVolume"),
                total_duration=profile.get("totalDuration"),
                order_usage=profile.get("orderUsage"),
                esim_list=json.dumps([profile]),
                package_list=json.dumps(profile.get("packageList"))
            )
            session.add(new_order)
            orders_created.append(qr_code)
        try:
            session.commit()
        except Exception as e:
            session.rollback()
            raise Exception(f"Database error: {str(e)}")

    return {"orderNo": order_no, "qrCodes": orders_created, "status": "confirmed"}


# -----------------------------
# 5. Query eSIM Status by ICCID
# -----------------------------
async def query_esim_by_iccid(iccid: str) -> dict:
    """
    Query the status of an eSIM using its ICCID.
    """
    url = f"{BASE_URL}/esim/query"
    payload = {
        "orderNo": "",
        "iccid": iccid,
        "pager": {"pageNum": 1, "pageSize": 20}
    }
    try:
        data = await api_post(url, payload, timeout=30)
        esim_list = data.get("obj", {}).get("esimList")
        if not esim_list or not isinstance(esim_list, list):
            return {"error": "No eSIM data returned."}
        return esim_list[0]
    except Exception as e:
        return {"error": str(e)}


async def fetch_esim_with_retry(iccid: str, retries: int = 3, delay: int = 1) -> Optional[dict]:
    """
    Retry querying the eSIM by ICCID if necessary.
    """
    for attempt in range(retries):
        data = await query_esim_by_iccid(iccid)
        if data and "iccid" in data:
            return data
        logger.warning(f"Retry {attempt+1}/{retries} failed for ICCID {iccid}")
        await asyncio.sleep(delay)
    logger.error(f"❌ All retries failed for ICCID {iccid}")
    return None


async def my_esim(user_id: str) -> list:
    """
    Retrieve the list of eSIMs associated with a user, updating their status from the API.
    """
    with SessionLocal() as session:
        iccid_tuples = session.query(Order.iccid).filter(Order.user_id == user_id).distinct().all()
    results = []
    for iccid_tuple in iccid_tuples:
        iccid = iccid_tuple[0]
        if iccid:
            logger.debug(f"[my_esim] Fetching API status for ICCID {iccid}")
            data = await fetch_esim_with_retry(iccid)
            results.append({"iccid": iccid, "data": data})
    return results


# -----------------------------
# 6. Cancel eSIM
# -----------------------------
async def cancel_esim(iccid: str = None, tran_no: str = None) -> dict:
    """
    Cancel an eSIM using either ICCID or transaction number.
    """
    if not iccid and not tran_no:
        return {"success": False, "errorMessage": "ICCID or tranNo required"}
    payload = {"iccid": iccid} if iccid else {"esimTranNo": tran_no}
    url = f"{BASE_URL}/esim/cancel"
    try:
        return await api_post(url, payload, timeout=15)
    except Exception as e:
        logger.warning(f"[Cancel API] Failed: {e}")
        return {"success": False, "errorMessage": str(e)}


# -----------------------------
# 7. Get Top-Up Packages
# -----------------------------
async def get_topup_packages(iccid: str) -> list:
    """
    Retrieve available top-up packages for a given eSIM (by ICCID).
    """
    url = f"{BASE_URL}/package/list"
    payload = {
        "type": "TOPUP",
        "iccid": iccid
    }
    try:
        result = await api_post(url, payload, timeout=30)
        if result.get("success"):
            return result["obj"].get("packageList", [])
    except Exception as e:
        logger.error(f"Top-Up packages error: {e}")
    return []


# -----------------------------
# 8. Top-Up eSIM
# -----------------------------
async def topup_esim(esim_tran_no: str, package_code: str, amount: int) -> dict:
    """
    Process a top-up request.
    """
    txn_id = str(uuid.uuid4())
    payload = {
        "esimTranNo": esim_tran_no,
        "packageCode": package_code,
        "price": amount,
        "transactionId": txn_id
    }
    logger.info(f"[Top-Up API] Top-Up requested: tranNo={esim_tran_no}, package={package_code}, amount={amount}, txn_id={txn_id}")
    url = f"{BASE_URL}/esim/topup"
    try:
        return await api_post(url, payload, timeout=15)
    except Exception as e:
        logger.warning(f"[Top-Up API] Failed: {e}")
        return {"success": False, "errorMessage": str(e)}


# -----------------------------
# 9. Update Usage and Order Data
# -----------------------------
def update_usage_by_iccid(db: Session, iccid: str, data: dict) -> bool:
    """
    Update an Order record's usage information in the database.
    """
    order = db.query(Order).filter(Order.iccid == iccid).first()
    if not order:
        logger.warning(f"[Usage Sync] Order not found for ICCID {iccid}")
        return False

    if "orderUsage" in data:
        order.order_usage = data["orderUsage"]

    if "lastUpdateTime" in data:
        try:
            order.last_update_time = datetime.fromisoformat(data["lastUpdateTime"])
        except Exception as e:
            logger.warning(f"[Usage Sync] Failed to parse lastUpdateTime for ICCID {iccid}: {e}")
            order.last_update_time = None

    order.updated_at = datetime.utcnow()
    db.commit()
    logger.info(f"[Usage Sync] Updated usage for ICCID {iccid} — {order.order_usage / 1024 / 1024:.1f} MB used")
    return True


def update_order_from_api(session: Session, iccid: str, data: dict) -> None:
    """
    Update an Order record in the database with the latest API data.
    """
    order = session.query(Order).filter(Order.iccid == iccid).first()
    if not order:
        logger.warning(f"[DB Sync] No order found for ICCID: {iccid}")
        return

    update_order_fields(order, data)
    session.commit()
    logger.info(f"[DB Sync] Order updated for ICCID: {iccid}")


def update_order_fields(order: Order, api_data: dict):
    """
    Update order fields safely based on API response data.
    """
    try:
        order.expired_time = api_data.get("expiredTime", order.expired_time)
        order.total_volume = api_data.get("totalVolume", order.total_volume)
        order.total_duration = api_data.get("totalDuration", order.total_duration)
        order.order_usage = api_data.get("orderUsage", order.order_usage)
        order.esim_status = api_data.get("esimStatus", order.esim_status)
        order.smdp_status = api_data.get("smdpStatus", order.smdp_status)

        # Update last sync time from API
        if "lastUpdateTime" in api_data:
            try:
                order.last_update_time = datetime.fromisoformat(api_data["lastUpdateTime"])
            except Exception:
                order.last_update_time = None

        order.updated_at = datetime.utcnow()
    except Exception as e:
        logger.warning(f"[DB Sync] Failed to update order fields for ICCID {order.iccid}: {e}")


# -----------------------------
# 10. Lookup ICCID from Transaction Number
# -----------------------------
async def query_allocated_profiles() -> List[dict]:
    """
    Query the API to retrieve allocated profiles.
    This version assumes an empty payload.
    """
    url = f"{BASE_URL}/esim/query"
    payload = {}
    try:
        data = await api_post(url, payload, timeout=30)
        if data.get("success") and isinstance(data.get("obj"), list):
            return data["obj"]
    except Exception as e:
        logger.warning(f"[Query Profiles] Failed to fetch allocated profiles: {e}")
    return []


async def get_iccid_from_tranno(tran_no: str) -> Optional[str]:
    """
    Retrieve the ICCID corresponding to a given transaction number.
    """
    profiles = await query_allocated_profiles()
    for profile in profiles:
        if profile.get("esimTranNo") == tran_no:
            return profile.get("iccid")
    return None
