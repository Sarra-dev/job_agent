import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException

logger = logging.getLogger("form_filler")
logging.basicConfig(level=logging.INFO)

def fill_application_form(job_url, user_data):
    options = webdriver.ChromeOptions()
    
    options.add_argument('--start-maximized')
    options.add_argument('--disable-blink-features=AutomationControlled')

    service = Service(executable_path="./chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(job_url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        final_url = driver.current_url
        logger.info(f"Final URL after redirects: {final_url}")

        external_sites = ["linkedin.com", "indeed.com", "workday.com", "greenhouse.io", "lever.co"]

        if any(ext in final_url for ext in external_sites):
            logger.warning(f"🔗 Redirected to external site: {final_url} — cannot auto-fill.")
            driver.save_screenshot("redirected.png")
            driver.quit()
            return False, f"Redirected to external site: {final_url} — manual apply needed."

        handle_cookie_consent(driver)
        time.sleep(2)

       
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        logger.info(f"Found {len(iframes)} iframes")

        form_filled = False

        for index, iframe in enumerate(iframes):
            driver.switch_to.default_content()
            driver.switch_to.frame(iframe)
            logger.info(f"Switched to iframe #{index}")

            num_inputs = len(driver.find_elements(By.TAG_NAME, "input"))
            logger.info(f"Iframe #{index} has {num_inputs} input fields")

            if num_inputs > 0:
                if fill_any_input_fields(driver, user_data):
                    form_filled = True
                    break  

        if not form_filled:
            logger.warning("❌ Could not find any form inputs in iframes. Trying main page.")
            driver.switch_to.default_content()
            if fill_any_input_fields(driver, user_data):
                form_filled = True

        screenshot_path = "form_result.png"
        driver.save_screenshot(screenshot_path)
        logger.info(f"Saved screenshot: {screenshot_path}")

        driver.quit()
        return form_filled, screenshot_path 

    except Exception as e:
        driver.save_screenshot("error.png")
        driver.quit()
        logger.error(f"Error: {e}")
        return False, str(e)



def handle_cookie_consent(driver, timeout=5):
    logger.info("🍪 Checking for cookie consent banner...")

    
    consent_texts = [
        "Accept", "Alle akzeptieren", "Zustimmen", "Agree", "OK",
        "Accept All", "Akzeptieren", "Accept necessary", "Nur notwendige"
    ]

   
    try:
        for text in consent_texts:
            xpath = f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]"
            logger.info(f"🔍 Trying XPath: {xpath}")
            try:
                button = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                button.click()
                logger.info(f"✅ Clicked cookie consent button: '{text}'")
                return True
            except TimeoutException:
                continue 

    except StaleElementReferenceException:
        logger.warning("⚠️ Stale element on main page, will retry...")

  
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    logger.info(f"🔍 Found {len(iframes)} iframes to check for cookie consent")

    for idx, iframe in enumerate(iframes):
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(iframe)
            logger.info(f"➡️ Switched to iframe #{idx}")
    

            for text in consent_texts:
                xpath = f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]"
                logger.info(f"🔍 Trying XPath in iframe: {xpath}")

                try:
                    button = WebDriverWait(driver, timeout).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    button.click()
                    logger.info(f"✅ Clicked cookie consent in iframe #{idx}: '{text}'")
                    driver.switch_to.default_content()
                    return True
                except TimeoutException:
                    continue

        except Exception as e:
            logger.warning(f"⚠️ Error while checking iframe #{idx}: {e}")
        finally:
            driver.switch_to.default_content()

    logger.info("❌ No cookie consent button found.")
    return False


def fill_any_input_fields(driver, user_data):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    name = user_data.get("name", "")
    email = user_data.get("email", "")
    phone = user_data.get("phone", "")

    inputs = driver.find_elements(By.TAG_NAME, "input")
    logger.info(f"Found {len(inputs)} input fields")

    filled_any = False

    for input_element in inputs:
        try:
            if not input_element.is_displayed():
                continue

            t = input_element.get_attribute("type")
            p = input_element.get_attribute("placeholder")
            name_attr = input_element.get_attribute("name")

            logger.info(f"Checking input: type={t}, placeholder={p}, name={name_attr}")

            if "mail" in (p or "").lower() or "mail" in (name_attr or ""):
                input_element.clear()
                input_element.send_keys(email)
                logger.info("Filled email")
            elif "phone" in (p or "").lower() or "phone" in (name_attr or "") or "tel" in (name_attr or ""):
                input_element.clear()
                input_element.send_keys(phone)
                logger.info("Filled phone")
            elif "name" in (p or "").lower() or "name" in (name_attr or ""):
                input_element.clear()
                input_element.send_keys(name)
                logger.info("Filled name")

        except Exception as e:
            logger.warning(f"Could not fill input: {e}")

    
    try:
        green_button = driver.find_element(By.XPATH, "//button[contains(., 'E-Mail-Benachrichtigung erstellen')]")
        green_button.click()
        logger.info("Clicked green submit button")

       
        WebDriverWait(driver, 10).until(
            EC.any_of(
                EC.url_changes(driver.current_url),
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'Danke')]")),
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'Thank you')]"))
            )
        )
        logger.info("✅ Form submitted and confirmed!")

    except Exception as e:
        logger.warning(f"Could not click or wait for confirmation: {e}")
