# buy_esim.py
import os
import requests
import asyncio
import uuid
from database import SessionLocal
import logging
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from models import Order
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List
import json


logger = logging.getLogger(__name__)

# Global constants for the ESIMAccess API
BASE_URL = "https://api.esimaccess.com/api/v1/open"
API_HEADERS = {
    "RT-AccessCode": os.getenv("REACT_APP_ESIM_API_Access_Code"),
    "RT-SecretKey": os.getenv("REACT_APP_ESIM_API_Secret_KEY"),
    "Content-Type": "application/json"
}

async def poll_profile(order_no: str, timeout: int = 30, interval: int = 5):
    """
    Poll the query_profile endpoint until an allocated profile is returned or the timeout is reached.
    """
    logger.info(f"⏳ Polling for profile allocation (order {order_no})...")

    start_time = asyncio.get_event_loop().time()
    while True:
        query_response = await query_profile(order_no)
        if query_response is not None:
            esim_list_raw = query_response.get("obj", {}).get("esimList", [])
            if esim_list_raw:
                logger.info(f"✅ QR profiles allocated: {len(esim_list_raw)}")
                return query_response
            else:
                logger.info("⚠️ Polling result: No profiles allocated yet.")
        else:
            logger.warning("⚠️ No response from query_profile API.")

        if asyncio.get_event_loop().time() - start_time > timeout:
            logger.error("❌ Timeout reached while waiting for profile allocation.")
            break

        await asyncio.sleep(interval)

    raise Exception("Timeout: eSIM profiles are still being allocated. Please try again later.")


# -----------------------------
# 0. User Payment Simulation
# -----------------------------
def user_payment_sync():
    """
    Simulate the user payment approval step.
    In a real scenario, this would integrate with a payment gateway.
    For now, we just generate and return a unique transaction ID.
    """
    return str(uuid.uuid4())

async def user_payment():
    return await asyncio.to_thread(user_payment_sync)

# -----------------------------
# 1. Check Balance
# -----------------------------
def check_balance_sync():
    url = f"{BASE_URL}/balance/query"
    response = requests.post(url, json={}, headers=API_HEADERS, timeout=30, verify=True)
    response.raise_for_status()
    return response.json()

async def check_balance():
    return await asyncio.to_thread(check_balance_sync)

# -----------------------------
# 2. Place Order
# -----------------------------
def place_order_sync(package_code: str, order_price: int, transaction_id: str):
    url = f"{BASE_URL}/esim/order"
    payload = {
        "transactionId": transaction_id,
        "amount": order_price,
        "packageInfoList": [
            {
                "packageCode": package_code,
                "count": 1,       # Default to ordering one package; adjust if needed.
                "price": order_price
                # Optionally add "periodNum": <value> for daily plans.
            }
        ]
    }
    response = requests.post(url, json=payload, headers=API_HEADERS, timeout=30, verify=True)
    response.raise_for_status()
    return response.json()

async def place_order(package_code: str, order_price: int, transaction_id: str):
    return await asyncio.to_thread(place_order_sync, package_code, order_price, transaction_id)

# -----------------------------
# 3. Query Profile (retrieve QR code/profile)
# -----------------------------
def query_profile_sync(order_no: str):
    """
    Calls the query API to get allocated eSIM profiles for a given order number.
    Uses a custom requests session with retries to mitigate SSL errors.
    """
    url = f"{BASE_URL}/esim/query"
    payload = {"orderNo": order_no, "pager": {"pageNum": 1, "pageSize": 20}}
    
    # Create a custom session with retries.
    session = requests.Session()
    retries = Retry(
        total=5, 
        backoff_factor=1, 
        status_forcelist=[502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    
    # Disable SSL verification (for development only)
    response = session.post(url, json=payload, headers=API_HEADERS, timeout=30, verify=True)
    response.raise_for_status()
    return response.json()

async def query_profile(order_no: str):
    return await asyncio.to_thread(query_profile_sync, order_no)

# -----------------------------
# 4. Process Purchase
# -----------------------------
async def process_purchase(package_code: str, user_id: str, order_price: int, retail_price: int, count: int = 1, period_num: int = None) -> dict:
    balance_data = await check_balance()
    available_balance = balance_data.get("obj", {}).get("balance", 0)
    if available_balance < order_price * count:
        logger.error(f"Insufficient funds: available {available_balance}, required {order_price * count}")
        raise Exception("Insufficient funds to place the order.")

    transaction_id = await user_payment()
    logger.info(f"Simulated transaction ID: {transaction_id}")

    def place_order_custom():
        url = f"{BASE_URL}/esim/order"
        # Calculate correct amount
        if period_num:  # daily plan
            final_count = 1
            total_amount = order_price * period_num
        else:  # multi-day plan
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

        response = requests.post(url, json=payload, headers=API_HEADERS, timeout=30, verify=True)
        response.raise_for_status()
        return response.json()

    order_response = await asyncio.to_thread(place_order_custom)
    if not order_response or not isinstance(order_response, dict):
        raise Exception("Order request failed or returned unexpected result.")
    logger.info(f"Order response: {order_response}")
    if not order_response.get("success"):
        raise Exception(f"Order failed: {order_response.get('errorMsg')}")
    order_no = order_response.get("obj", {}).get("orderNo")
    if not order_no:
        raise Exception("Order API did not return an orderNo.")

    await asyncio.sleep(3)
    query_response = await poll_profile(order_no, timeout=30, interval=5)
    if not query_response or not isinstance(query_response, dict):
        raise Exception("Polling failed: no profile response received.")

    esim_list_raw = query_response.get("obj", {}).get("esimList", [])
    if not esim_list_raw:
        raise Exception("No eSIM profile returned.")

    profile = esim_list_raw[0]
    qr_codes = [profile.get("qrCodeUrl") for profile in esim_list_raw if profile.get("qrCodeUrl")]
    if not qr_codes:
        raise Exception("No QR codes found in the response.")

  
    session = SessionLocal()
    orders_created = []
    try:
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
                esim_list=json.dumps([profile]),  # store only 1 profile per row
                package_list=json.dumps(profile.get("packageList"))
            )
            session.add(new_order)
            orders_created.append(qr_code)

        session.commit()
    except Exception as e:
        session.rollback()
        raise Exception(f"Database error: {str(e)}")
    finally:
        session.close()

    return {"orderNo": order_no, "qrCodes": orders_created, "status": "confirmed"}

# -----------------------------
# 5. Query eSIM Status by ICCID
# -----------------------------
def query_esim_by_iccid(iccid: str) -> dict:
    url = f"{BASE_URL}/esim/query"
    payload = {
        "orderNo": "",
        "iccid": iccid,
        "pager": {
            "pageNum": 1,
            "pageSize": 20
        }
    }
    try:
        response = requests.post(
            url,
            json=payload,
            headers=API_HEADERS,
            timeout=30,
            verify=True
        )
        response.raise_for_status()
        data = response.json()

        esim_list = data.get("obj", {}).get("esimList")
        if not esim_list or not isinstance(esim_list, list):
            return {"error": "No eSIM data returned."}

        return esim_list[0]
    except Exception as e:
        return {"error": str(e)}
    
async def fetch_esim_with_retry(iccid, retries=3, delay=1):
    for attempt in range(retries):
        data = await asyncio.to_thread(query_esim_by_iccid, iccid)
        if data and "iccid" in data:
            return data
        logging.warning(f"Retry {attempt+1}/{retries} failed for ICCID {iccid}")
        await asyncio.sleep(delay)
    logging.error(f"❌ All retries failed for ICCID {iccid}")
    return None
    
async def my_esim(user_id: str) -> list:
    session = SessionLocal()
    try:
        iccids = session.query(Order.iccid).filter(Order.user_id == user_id).distinct().all()
        results = []
        for iccid_tuple in iccids:
            iccid = iccid_tuple[0]
            if iccid:
                logger.debug(f"[my_esim] Fetching API status for ICCID {iccid}")
                data = await fetch_esim_with_retry(iccid)
                results.append({"iccid": iccid, "data": data})
        return results
    finally:
        session.close()    

def cancel_esim(iccid: str = None, tran_no: str = None) -> dict:
    if not iccid and not tran_no:
        return {"success": False, "errorMessage": "ICCID or tranNo required"}

    payload = {"iccid": iccid} if iccid else {"esimTranNo": tran_no}
    try:
        response = requests.post(
            f"{BASE_URL}/esim/cancel",
            headers=API_HEADERS,
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.warning(f"[Cancel API] Failed: {e}")
        return {"success": False, "errorMessage": str(e)}

async def get_topup_packages(iccid: str) -> list:
    url = f"{BASE_URL}/package/list"
    payload = {
        "type": "TOPUP",
        "iccid": iccid
    }
    try:
        response = requests.post(url, json=payload, headers=API_HEADERS, timeout=30)
        response.raise_for_status()
        result = response.json()
        if result.get("success"):
            return result["obj"].get("packageList", [])
    except Exception as e:
        logger.error(f"Top-Up packages error: {e}")
    return []

def topup_esim(esim_tran_no: str, package_code: str, amount: int) -> dict:
    txn_id = str(uuid.uuid4())
    payload = {
        "esimTranNo": esim_tran_no,
        "packageCode": package_code,
        "price": amount,
        "transactionId": txn_id
    }
    logger.info(f"[Top-Up API] Top-Up requested: tranNo={esim_tran_no}, package={package_code}, amount={amount}, txn_id={txn_id}")
    try:
        response = requests.post(
            f"{BASE_URL}/esim/topup",
            headers=API_HEADERS,
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.warning(f"[Top-Up API] Failed: {e}")
        return {"success": False, "errorMessage": str(e)}

def update_usage_by_iccid(db: Session, iccid: str, data: dict) -> bool:
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
    Update Order row in DB using latest API response for a given ICCID.
    """
    order = session.query(Order).filter(Order.iccid == iccid).first()
    if not order:
        logger.warning(f"[DB Sync] No order found for ICCID: {iccid}")
        return

    update_order_fields(order, data)
    session.commit()
    logger.info(f"[DB Sync] Order updated for ICCID: {iccid}")

async def get_iccid_from_tranno(tran_no: str) -> Optional[str]:
    """
    Get ICCID by querying the profile with tran_no.
    Used after top-up to re-sync data.
    """
    try:
        resp = query_allocated_profiles()
        for profile in resp:
            if profile.get("esimTranNo") == tran_no:
                return profile.get("iccid")
    except Exception as e:
        logger.warning(f"[Lookup] Failed to get ICCID from tranNo {tran_no}: {e}")
    return None

def query_allocated_profiles() -> List[dict]:
    url = f"{BASE_URL}/esim/query"
    try:
        response = requests.post(url, headers=API_HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("success") and isinstance(data.get("obj"), list):
            return data["obj"]
    except Exception as e:
        logger.warning(f"[Query Profiles] Failed to fetch allocated profiles: {e}")
    return []

def update_order_fields(order: Order, api_data: dict):
    """
    Safely updates Order fields based on latest API data.
    """
    if not order or not api_data:
        return

    try:
        order.expired_time = api_data.get("expiredTime", order.expired_time)
        order.total_volume = api_data.get("totalVolume", order.total_volume)
        order.total_duration = api_data.get("totalDuration", order.total_duration)
        order.order_usage = api_data.get("orderUsage", order.order_usage)
        order.esim_status = api_data.get("esimStatus", order.esim_status)
        order.smdp_status = api_data.get("smdpStatus", order.smdp_status)

        # Extra: update last sync time from usage API
        if "lastUpdateTime" in api_data:
            try:
                order.last_update_time = datetime.fromisoformat(api_data["lastUpdateTime"])
            except Exception:
                order.last_update_time = None

        order.updated_at = datetime.utcnow()
    except Exception as e:
        logger.warning(f"[DB Sync] Failed to update order fields for ICCID {order.iccid}: {e}")
