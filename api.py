import requests

def get_all_rates():
    """
    Fetches real-time USD rates and calculates cross rates for EUR and GBP to TRY.
    """
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        usd_to_try = data["rates"]["TRY"]
        eur_to_try = usd_to_try / data["rates"]["EUR"]
        gbp_to_try = usd_to_try / data["rates"]["GBP"]
        
        return {
            "USD/TRY": usd_to_try,
            "EUR/TRY": eur_to_try,
            "GBP/TRY": gbp_to_try
        }
    except Exception as e:
        print(f"API Error: {e}. Using fallback rates.")
        return {"USD/TRY": 32.20, "EUR/TRY": 35.10, "GBP/TRY": 40.80}