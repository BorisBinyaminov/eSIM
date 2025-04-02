# buy_esim.py
import os
import requests
import asyncio
import uuid
from database import SessionLocal
import logging
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter



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
    start_time = asyncio.get_event_loop().time()
    while True:
        query_response = await query_profile(order_no)
        if query_response is not None:
            esim_list_raw = query_response.get("obj", {}).get("esimList", [])
            if esim_list_raw:
                return query_response
        # If query_response is None or no profiles found, wait and try again.
        if asyncio.get_event_loop().time() - start_time > timeout:
            break
        await asyncio.sleep(interval)
    raise Exception("Timeout: eSIM profiles are still being allocated; please try again later.")

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
    response = requests.post(url, json={}, headers=API_HEADERS, timeout=600, verify=False)
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
    response = requests.post(url, json=payload, headers=API_HEADERS, timeout=600, verify=False)
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
    response = session.post(url, json=payload, headers=API_HEADERS, timeout=600, verify=False)
    response.raise_for_status()
    return response.json()

async def query_profile(order_no: str):
    return await asyncio.to_thread(query_profile_sync, order_no)

# -----------------------------
# 4. Process Purchase
# -----------------------------
async def process_purchase(package_code: str, user_id: str, order_price: int, retail_price: int) -> dict:
    """
    Process the eSIM purchase:
      1. Check Balance.
      2. Payment (simulated) to obtain a transaction ID.
      3. Place Order via the order API.
      4. Query Profile to retrieve allocated eSIM profile details.
      5. Update Database: Create a new Order record including additional fields.
      6. Return purchase details (orderNo, qrCode, etc.)
    """
    # Step 1: Check Balance
    balance_data = await check_balance()
    available_balance = balance_data.get("obj", {}).get("balance", 0)
    if available_balance < order_price:
        logger.error(f"Insufficient funds: available {available_balance}, required {order_price}")
        raise Exception("Insufficient funds to place the order. Please add funds or choose a different package.")
    
    # Step 2: Payment Step (simulate and get transaction ID)
    transaction_id = await user_payment()
    logger.info(f"Simulated transaction ID: {transaction_id}")
    
    # Step 3: Place Order using the external transaction ID
    order_response = await place_order(package_code, order_price, transaction_id)
    order_no = order_response.get("obj", {}).get("orderNo")
    if not order_no:
        raise Exception("Order API did not return an orderNo.")
    
    # Wait 3 seconds before polling for the allocated profile.
    await asyncio.sleep(3)

    # Step 4: Query Profile – retrieve the allocated profile details.
    query_response = await poll_profile(order_no, timeout=30, interval=5)
    esim_list_raw = query_response.get("obj", {}).get("esimList", [])
    if not esim_list_raw:
        error_code = query_response.get("errorCode")
        if error_code == "200010":
            raise Exception("eSIM profiles are still being allocated; please try again later.")
        raise Exception("Query API did not return any eSIM profiles.")
    
    profile = esim_list_raw[0]  # Use the first allocated profile.
    qr_code = profile.get("qrCodeUrl")
    if not qr_code:
        raise Exception("QR code not found in the query response.")
    
    # Extract additional details from the profile.
    iccid_value = profile.get("iccid")  # New: retrieve ICCID.
    esim_status = profile.get("esimStatus")
    smdp_status = profile.get("smdpStatus")
    expired_time = profile.get("expiredTime")  # ISO string; convert if needed.
    total_volume = profile.get("totalVolume")
    total_duration = profile.get("totalDuration")
    order_usage = profile.get("orderUsage")
    package_list = profile.get("packageList")
    
    # Convert the full esimList to a JSON string for storage.
    import json
    esim_list_str = json.dumps(esim_list_raw)
    package_list_str = json.dumps(package_list) if package_list is not None else None
    
    # Step 5: Update Database
    from models import Order
    session = SessionLocal()
    try:
        new_order = Order(
            user_id=user_id,
            package_code=package_code,
            order_id=order_no,
            transaction_id=transaction_id,
            iccid=iccid_value,              # New: store the ICCID.
            count=1,                        # Default; can be updated in future.
            period_num=None,                # TBD for daily plans.
            price=order_price,
            retail_price=retail_price,
            qr_code=qr_code,
            status="confirmed",
            details=None,
            esim_status=esim_status,
            smdp_status=smdp_status,
            expired_time=expired_time,
            total_volume=total_volume,
            total_duration=total_duration,
            order_usage=order_usage,
            esim_list=esim_list_str,
            package_list=package_list_str
        )
        session.add(new_order)
        session.commit()
    except Exception as e:
        session.rollback()
        raise Exception(f"Error updating database: {str(e)}")
    finally:
        session.close()
    
    # Step 6: Return the purchase result.
    return {"orderNo": order_no, "qrCode": qr_code, "status": "confirmed"}
