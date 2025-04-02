# buy_esim.py
import os
import requests
import asyncio

def check_balance_sync():
    url = "https://api.esimaccess.com/api/v1/open/balance/query"
    headers = {
        "RT-AccessCode": os.getenv("REACT_APP_ESIM_API_Access_Code"),
        "RT-SecretKey": os.getenv("REACT_APP_ESIM_API_Secret_KEY"),
        "Content-Type": "application/json"
    }
    # Send an empty JSON body; adjust if needed
    response = requests.post(url, json={}, headers=headers, timeout=600)
    response.raise_for_status()
    return response.json()

async def check_balance():
    # Run the synchronous call in a separate thread
    return await asyncio.to_thread(check_balance_sync)
