import json
import getpass
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import config

class TwitterAuth:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.driver = None

    def login(self):
        """
        Logs into X.com in headless mode and saves session cookies.
        """
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        
        self.driver = webdriver.Firefox(options=options)
        print("🚀 Starting headless browser...")

        try:
            self.driver.get(config.LOGIN_URL)
            print(f"Navigated to {config.LOGIN_URL}")

            # Step 1: Enter Username
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[autocomplete="username"]'))
            )
            print("👤 Found username field. Entering username...")
            username_field.send_keys(self.username)

            next_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//span[text()="Next"]'))
            )
            next_button.click()
            print("✅ Clicked 'Next' button.")

            # Step 2: Handle Potential Verification
            try:
                verification_field = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-testid="ocfEnterTextTextInput"]'))
                )
                print("🤔 Verification step detected. Re-entering username...")
                verification_field.send_keys(self.username)
                
                verify_next_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '//span[text()="Next"]'))
                )
                verify_next_button.click()
                print("✅ Handled verification step.")
            except TimeoutException:
                print("✅ No verification step needed. Proceeding to password.")
                pass

            # Step 3: Enter Password
            password_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[autocomplete="current-password"]'))
            )
            print("🔑 Found password field. Entering password...")
            password_field.send_keys(self.password)
            
            login_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//span[contains(text(),"Log in")]'))
            )
            login_button.click()
            print("✅ Clicked 'Log in' button.")

            # Step 4: Verify Login & Save Cookies
            print("⏳ Verifying login success...")
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[aria-label="Home"]'))
            )
            
            print("\n🎉 Login successful!")
            self._save_cookies()

        except TimeoutException:
            print(f"\n❌ Login Failed: A timeout occurred. This could be due to:")
            print("- Incorrect username or password.")
            print("- A CAPTCHA challenge that cannot be solved in headless mode.")
            print("- Slow network connection or a change in X.com's login page structure.")
        
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        finally:
            if self.driver:
                print("🔚 Closing browser.")
                self.driver.quit()

    def _save_cookies(self):
        cookies = self.driver.get_cookies()
        with open(config.COOKIES_FILENAME, "w") as f:
            json.dump(cookies, f, indent=2)
        print(f"🍪 Cookies have been saved to '{config.COOKIES_FILENAME}'")

def main():
    username = input("Enter your X.com username or email: ")
    password = getpass.getpass("Enter your X.com password: ")
    if username and password:
        auth = TwitterAuth(username, password)
        auth.login()
    else:
        print("❌ Username and password cannot be empty. Aborting.")

if __name__ == "__main__":
    main()
