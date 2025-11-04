import asyncio
import os, time
# from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import pandas as pd
from tabulate import tabulate
import requests
from telegram import Bot
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

class ChartInkCSVDownloader:
    def __init__(self, url, download_dir=None, headless=True):

        self.url = url
        self.headless = headless
        self.driver = None
        
        if download_dir is None:
            self.download_dir = os.path.join(os.getcwd(), "downloads")
        else:
            self.download_dir = download_dir

        os.makedirs(self.download_dir, exist_ok=True)

    def setup_driver(self):

        chrome_options = Options()
        
        # Set download preferences
        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(120)
            return True
        except Exception as e:
            print(f"Error setting up Chrome driver: {e}")
            print("Make sure ChromeDriver is installed and in PATH")
            return False
    
    def wait_for_page_load(self, timeout=120):
        """Wait for the page to load completely"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            time.sleep(5)  # Additional wait for dynamic content
            return True
        except TimeoutException:
            print("Page load timeout")
            return False
    
    def find_csv_button(self):
        """Find the CSV download button using the analyzed structure"""
        try:
            # print("Looking for CSV download button...")

            # Strategy 1: Find all divs with the target class and filter by text
            target_class = "secondary-button w-fit px-2 lg:px-4 py-1.5 opacity-100 cursor-pointer"
            
            # Use CSS selector with exact class match
            css_selector = f'div[class="{target_class}"]'
            elements = self.driver.find_elements(By.CSS_SELECTOR, css_selector)
            
            if not elements:
                # Fallback: Try partial class matching
                elements = self.driver.find_elements(By.CSS_SELECTOR, 'div.secondary-button.cursor-pointer')
            # print(f"Found {len(elements)} potential button elements")
            # Filter by text content to find CSV button
            for element in elements:
                element_text = element.text.strip()
                # print(f"Checking element with text: '{element_text}'")
                if element_text == 'CSV':
                    print("✅ Found CSV button!")
                    return element
            
            print("CSV button not found with any strategy")
            return None
            
        except Exception as e:
            print(f"Error finding CSV button: {e}")
            return None
    
    def click_csv_button(self):
        try:
            # Wait for the button to be present
            csv_button = None
            max_attempts = 5
            
            for attempt in range(max_attempts):
                csv_button = self.find_csv_button()
                if csv_button:
                    break
                print(f"Attempt {attempt + 1}: CSV button not found, waiting...")
                time.sleep(2)
            
            # Scroll to the button
            self.driver.execute_script("arguments[0].scrollIntoView(true);", csv_button)
            time.sleep(1)
            
            # Try different clicking methods
            click_methods = [
                lambda: csv_button.click(),
                lambda: self.driver.execute_script("arguments[0].click();", csv_button),
                lambda: self.driver.execute_script("arguments[0].dispatchEvent(new Event('click', {bubbles: true}));", csv_button)
            ]
            
            for i, click_method in enumerate(click_methods):
                try:
                    click_method()
                    # print(f"CSV button clicked successfully (method {i+1})")
                    return True
                except Exception as e:
                    print(f"Click method {i+1} failed: {e}")
                    continue
            
            return False
            
        except Exception as e:
            print(f"Error clicking CSV button: {e}")
            return False
    
    def wait_for_download(self, timeout=30):
        # print("Waiting for download to complete...")
        
        # Get initial files in download directory
        initial_files = set(os.listdir(self.download_dir))
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_files = set(os.listdir(self.download_dir))
            new_files = current_files - initial_files
            
            # Check for new files
            for file in new_files:
                file_path = os.path.join(self.download_dir, file)
                
                # Skip temporary files
                if file.endswith('.crdownload') or file.endswith('.tmp'):
                    continue
                
                # Check if it's a CSV file
                if file.endswith('.csv'):
                    print(f"✅ Download completed: {file}")
                    return file_path
            
            time.sleep(1)
        
        print("❌ Download timeout reached")
        return None
    
    def download_csv(self):
        if not self.setup_driver():
            return None
        
        try:
            print(f"🔄️ Loading page: {self.url}")
            self.driver.get(self.url)
            
            if not self.wait_for_page_load():
                print("Failed to load page completely")
                return None
            
            print("✅ Page loaded successfully")
            
            # Click the CSV download button
            if not self.click_csv_button():
                print("❌ Failed to click CSV button")
                return None
            
            # Wait for download
            csv_file_path = self.wait_for_download()
            
            if csv_file_path:
                # print(f"✅ CSV file downloaded successfully: {csv_file_path}")
                return csv_file_path
            else:
                print("❌ Download failed or timed out")
                return None
                
        except Exception as e:
            print(f"Error during download process: {e}")
            return None
        finally:
            if self.driver:
                self.driver.quit()

def rename_with_date_suffix(file_path: str):
    file = Path(file_path)
    if file.exists() and file.suffix == ".csv":
        date_str = datetime.today().strftime("%d-%m-%Y")
        new_file = file.with_name(f"{file.stem}_{date_str}{file.suffix}")
        if os.path.exists(new_file):
            os.remove(new_file)
        file.rename(new_file)
        return new_file
    else:
        return None

def print_csv_as_table(file_path: str):
    try:
        TOKEN = os.getenv("TOKEN")
        CHAT_ID = os.getenv("CHAT_ID")
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

        df = pd.read_csv(file_path)
        selected = df[['Symbol', '%Chg']]

        print(tabulate(selected, headers='keys', tablefmt='psql', showindex=False))

        # MESSAGE = tabulate(selected, headers='keys', tablefmt='psql', showindex=False)

        message_lines = []
        for _, row in selected.iterrows():
            message_lines.append(f"{row['Symbol']}: {row['%Chg']}%")
        
        message = "\n".join(message_lines)
        data = {"chat_id": CHAT_ID, "text": message}

        response = requests.post(url, data=data)
        print("Status:", response.status_code)
        print(response.text)  # Check for errors
    except Exception as e:
        print(f"Error: {e}")

async def post_to_telegram(file_path: str):
    try:
        bot = Bot(token=os.getenv("TOKEN"))
        chat_id = os.getenv("CHAT_ID")
    
        df = pd.read_csv(file_path)
        selected = df[['Symbol', '%Chg']]
        
        MAX_MESSAGE_LENGTH = 4000  # Leave some buffer
        
        header = f"<b>HMA Scanned Stocks</b>\n{datetime.now().strftime('Time: %d %b, %Y AT %I:%M %p')}\n\n<pre>"
        table_header = "Symbol            %Chg\n" + "-" * 25 + "\n"
        footer = "</pre>"
        
        current_message = header + table_header
        message_count = 1
        
        for _, row in selected.iterrows():
            symbol = str(row['Symbol']).ljust(15)
            chg = f"{row['%Chg']:>8}%"
            line = f"{symbol}{chg}\n"
            
            # Check if adding this line exceeds limit
            if len(current_message + line + footer) > MAX_MESSAGE_LENGTH:
                # Send current message
                await bot.send_message(chat_id=chat_id, text=current_message + footer, parse_mode="HTML")
                
                # Start new message
                message_count += 1
                current_message = f"<b>HMA Scanned Stocks (Part {message_count})</b>\n{datetime.now().strftime('Time: %d %b, %Y AT %I:%M %p')}\n\n<pre>" + table_header
            
            current_message += line
        
        # Send remaining message
        if current_message != header + table_header:
            await bot.send_message(chat_id=chat_id, text=current_message + footer, parse_mode="HTML")
        
        # Send CSV file
        with open(file_path, "rb") as f:
            await bot.send_document(chat_id=chat_id, document=f, filename=os.path.basename(file_path))
        print("✅ CSV file sent to Telegram successfully")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    
    # load_dotenv()
    print(f"🟢 Starting ChartInk VCP Volume Scan for {datetime.today().strftime('%d-%m-%Y')}")

    # url = "https://chartink.com/screener/profit-jump-by-200"
    # url = "https://chartink.com/screener/vcp-volume-scan-3"
    url = "https://chartink.com/screener/small-cap-stocks"

    downloader = ChartInkCSVDownloader(url, headless=True)  # Set to False to see browser
    csv_file = downloader.download_csv()

    if os.path.exists(csv_file):
        file_path = rename_with_date_suffix(csv_file)
        print(f"✅ CSV file downloaded successfully to: {file_path}")
    else:
        print("❌ Failed to download CSV file")
        exit(1)

    # print_csv_as_table(file_path)
    asyncio.run(post_to_telegram(file_path))
