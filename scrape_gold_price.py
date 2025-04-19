import json
import time
import requests # Added for Telegram API calls
import os # Added to potentially read from environment variables later
from dotenv import load_dotenv
load_dotenv() # Load variables from .env file

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuration (Loaded from .env) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")
WHATSAPP_CHAT_ID = os.getenv("WHATSAPP_CHAT_ID")
WHATSAPP_SESSION = os.getenv("WHATSAPP_SESSION")
# ---------------------------------------

def send_to_telegram(bot_token, chat_id, message_text):
    """Sends a message to a Telegram chat using the Bot API."""
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message_text,
        'parse_mode': 'Markdown' # Optional: for formatting
    }
    try:
        response = requests.post(api_url, data=payload, timeout=10)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        print("Message successfully sent to Telegram.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Telegram: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while sending to Telegram: {e}")
        return False

def send_to_whatsapp(message_text):
    """Sends a message via the WhatsApp API."""
    payload = {
        "chatId": WHATSAPP_CHAT_ID,
        "reply_to": None,
        "text": message_text,
        "linkPreview": True,
        "linkPreviewHighQuality": False,
        "session": WHATSAPP_SESSION
    }
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    try:
        # Use json parameter for requests library to automatically handle JSON encoding and headers
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        print(f"Message successfully sent to WhatsApp ({WHATSAPP_CHAT_ID}).")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to WhatsApp: {e}")
        # Attempt to print response details if available
        if 'response' in locals() and response is not None:
             try:
                 print(f"Response status: {response.status_code}")
                 print(f"Response text: {response.text}")
             except Exception as detail_e:
                 print(f"Could not retrieve response details: {detail_e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while sending to WhatsApp: {e}")
        return False

def format_telegram_message(gold_data_list):
    """Formats the gold price data for a Telegram message."""
    if not gold_data_list or isinstance(gold_data_list, dict) and "error" in gold_data_list:
         return "Failed to retrieve gold price data."

    message = "*Harga Emas Logam Mulia Hari Ini*\n\n"
    for item in gold_data_list:
        weight = item.get('weight', 'N/A')
        buy_price = item.get('buy_price_str', 'N/A')
        sell_price = item.get('sell_price_str', 'N/A')
        if(buy_price == ""):
            message += f"\n\n*{weight}*\n"
        else:   
            message += f"⚖️ *{weight}*: {buy_price} | {sell_price}\n"
    return message


def scrape_gold_price():
    """
    Scrapes gold price data from logammulia.com using Selenium
    and returns it as a list of dictionaries or an error dictionary.
    """
    url = "https://www.logammulia.com/en/harga-emas-hari-ini"
    gold_prices = []

    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Run headless (no browser window) - Re-enabled
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    # Setup WebDriver
    try:
        print("Setting up WebDriver...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print(f"Navigating to {url}...")
        driver.get(url)

        wait = WebDriverWait(driver, 30) # Increased wait time further
        price_table_locator = (By.CSS_SELECTOR, ".table")
        print("Waiting for price table...")
        price_table = wait.until(EC.presence_of_element_located(price_table_locator))
        # Add a small delay after table is present, sometimes helps with dynamic loading
        time.sleep(2)
        print("Price table found.")

        rows = price_table.find_elements(By.XPATH, ".//tbody/tr")
        print(f"Found {len(rows)} rows in the table.")

        if not rows:
             print("No data rows found in the table. The website structure might have changed.")
             return {"error": "No data rows found"}

        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 3:
                    weight_text = cells[0].text.strip()
                    buy_price_text = cells[1].text.strip()
                    sell_price_text = cells[2].text.strip()

                    buy_price = buy_price_text.replace('Rp', '').replace('.', '').replace(',', '').strip()
                    sell_price = sell_price_text.replace('Rp', '').replace('.', '').replace(',', '').strip()

                    try:
                        buy_price_num = int(buy_price) if buy_price.isdigit() else None
                    except ValueError: buy_price_num = None
                    try:
                        sell_price_num = int(sell_price) if sell_price.isdigit() else None
                    except ValueError: sell_price_num = None

                    gold_prices.append({
                        "weight": weight_text,
                        "buy_price_str": buy_price_text,
                        "buy_price_num": buy_price_num,
                        "sell_price_str": sell_price_text,
                        "sell_price_num": sell_price_num
                    })
                else:
                    gold_prices.append({
                        "weight": row.text,
                        "buy_price_str": "",
                        "buy_price_num": "",
                        "sell_price_str": "",
                        "sell_price_num": ""
                    })
            except Exception as e:
                print(f"Error processing row: {row.text} - {e}")
                continue

    except Exception as e:
        print(f"An error occurred during scraping: {e}")
        return {"error": str(e)}
    finally:
        if 'driver' in locals() and driver:
            print("Closing browser...")
            driver.quit()

    if not gold_prices:
        print("No gold prices were successfully extracted.")
        return {"error": "No data extracted"}

    return gold_prices # Return list directly

if __name__ == "__main__":
    print("Starting gold price scraping...")
    scraped_data = scrape_gold_price() # Get list or error dict

    # Print JSON output regardless
    print("\n--- JSON Output ---")
    print(json.dumps(scraped_data, indent=4))
    print("-------------------")

    # Check if scraping was successful before sending
    if isinstance(scraped_data, list) and scraped_data:
        # Check if environment variables are loaded
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID or not WHATSAPP_API_URL or not WHATSAPP_CHAT_ID or not WHATSAPP_SESSION:
            print("\nOne or more configuration variables are missing from the .env file or environment.")
            print("Please ensure TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, WHATSAPP_API_URL, WHATSAPP_CHAT_ID, and WHATSAPP_SESSION are set.")
        else:
            print("\nAttempting to send data to Telegram...")
            telegram_message = format_telegram_message(scraped_data)
            # Split message if too long for Telegram (max 4096 chars)
            max_len = 4096
            telegram_sent = False # Initialize flag
            if len(telegram_message) > max_len:
                # --- Send to Telegram (Multipart) ---
                print("Message too long for Telegram, sending in parts...")
                parts_sent_successfully = True
                for i in range(0, len(telegram_message), max_len):
                    part = telegram_message[i:i+max_len]
                    if not send_to_telegram(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, part):
                        parts_sent_successfully = False
                        print(f"Failed to send part {i//max_len + 1} to Telegram. Aborting further sends.")
                        break # Stop if one part fails
                    time.sleep(1) # Small delay between parts
                telegram_sent = parts_sent_successfully
                # --- End Send to Telegram (Multipart) ---
            else:
                 # --- Send to Telegram (Single part) ---
                 telegram_sent = send_to_telegram(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, telegram_message)
                 # --- End Send to Telegram (Single part) ---

            # --- Send to WhatsApp (if Telegram was successful) ---
            if telegram_sent:
                print("\nAttempting to send data to WhatsApp...")
                send_to_whatsapp(telegram_message) # Send the full original message
            else:
                print("\nSkipping WhatsApp send because Telegram send failed or was incomplete.")
            # --- End Send to WhatsApp ---
    elif isinstance(scraped_data, dict) and "error" in scraped_data:
        print(f"\nScraping failed: {scraped_data['error']}")
        # Optionally send error notification to Telegram
        # if "PLACEHOLDER" not in TELEGRAM_BOT_TOKEN and "PLACEHOLDER" not in TELEGRAM_CHAT_ID:
        #     send_to_telegram(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, f"Gold price scraping failed: {scraped_data['error']}")
    else:
        print("\nNo data scraped or an unknown issue occurred.")

    print("\nScript finished.")
