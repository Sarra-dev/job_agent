import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

logger = logging.getLogger("form_filler")
logging.basicConfig(level=logging.INFO)

def fill_application_form(job_url, user_data):
    options = webdriver.ChromeOptions()
    
    options.add_argument('--start-maximized')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=VizDisplayCompositor')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    service = Service(executable_path="./chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    try:
        driver.get(job_url)

        # Wait for page to load completely
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)  # Additional wait for dynamic content

        final_url = driver.current_url
        logger.info(f"Final URL after redirects: {final_url}")

        external_sites = ["linkedin.com", "indeed.com", "workday.com", "greenhouse.io", "lever.co", "jobvite.com", "bamboohr.com"]

        if any(ext in final_url for ext in external_sites):
            logger.warning(f"🔗 Redirected to external site: {final_url} — cannot auto-fill.")
            driver.save_screenshot("redirected.png")
            driver.quit()
            return False, f"Redirected to external site: {final_url} — manual apply needed."

        # Handle overlays and cookies first, but don't let it interfere with form filling
        handle_overlays_and_modals(driver)
        time.sleep(3)  # Wait for overlays to be fully removed

        # Try to find and fill forms in multiple attempts
        form_filled = False
        attempts = 0
        max_attempts = 3

        while not form_filled and attempts < max_attempts:
            attempts += 1
            logger.info(f"Form filling attempt #{attempts}")
            
            # First, try iframes
            form_filled = try_fill_in_iframes(driver, user_data)
            
            # If no luck with iframes, try main page
            if not form_filled:
                logger.info("Trying main page for form fields...")
                driver.switch_to.default_content()
                form_filled = fill_any_input_fields(driver, user_data)
            
            if not form_filled:
                logger.info("Waiting for dynamic content and retrying...")
                
                # Remove any remaining overlays before retry
                driver.execute_script("""
                    document.querySelectorAll('.mfp-container, .mfp-bg, .mfp-wrap, .modal-backdrop').forEach(el => {
                        el.style.display = 'none';
                        el.remove();
                    });
                """)
                
                time.sleep(3)
                # Scroll down to trigger any lazy-loaded content
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)

        screenshot_path = "form_result.png"
        driver.save_screenshot(screenshot_path)
        logger.info(f"Saved screenshot: {screenshot_path}")

        # If form was filled, try to submit
        # if form_filled:
            #try_submit_form(driver)

        driver.quit()
        return form_filled, screenshot_path 

    except Exception as e:
        driver.save_screenshot("error.png")
        driver.quit()
        logger.error(f"Error: {e}")
        return False, str(e)


def try_fill_in_iframes(driver, user_data):
    """Try to fill forms within iframes"""
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        logger.info(f"Found {len(iframes)} iframes")

        for index, iframe in enumerate(iframes):
            try:
                driver.switch_to.default_content()
                
                # Wait for iframe to be available
                WebDriverWait(driver, 5).until(EC.frame_to_be_available_and_switch_to_it(iframe))
                logger.info(f"Switched to iframe #{index}")

                # Check if this iframe has form fields
                inputs = driver.find_elements(By.TAG_NAME, "input")
                selects = driver.find_elements(By.TAG_NAME, "select")
                textareas = driver.find_elements(By.TAG_NAME, "textarea")
                
                total_fields = len(inputs) + len(selects) + len(textareas)
                logger.info(f"Iframe #{index} has {total_fields} form fields")

                if total_fields > 0:
                    if fill_any_input_fields(driver, user_data):
                        logger.info(f"Successfully filled form in iframe #{index}")
                        return True

            except Exception as e:
                logger.warning(f"Error processing iframe #{index}: {e}")
                continue
            finally:
                driver.switch_to.default_content()

    except Exception as e:
        logger.warning(f"Error processing iframes: {e}")

    return False


def handle_overlays_and_modals(driver, timeout=10):
    """Handle all types of overlays, modals, and popups that might block interactions"""
    logger.info("🍪 Handling overlays, modals, and cookie consent...")

    # First, try to close any modal/popup containers
    modal_close_selectors = [
        # Magnific Popup (mfp) - the one causing your issue
        "//div[contains(@class, 'mfp-container')]//button[contains(@class, 'mfp-close')]",
        "//div[contains(@class, 'mfp-container')]//a[contains(@class, 'mfp-close')]",
        "//button[contains(@class, 'mfp-close')]",
        "//a[contains(@class, 'mfp-close')]",
        
        # Generic modal close buttons
        "//div[contains(@class, 'modal')]//button[contains(@class, 'close')]",
        "//div[contains(@class, 'popup')]//button[contains(@class, 'close')]",
        "//div[contains(@class, 'overlay')]//button[contains(@class, 'close')]",
        "//button[contains(@aria-label, 'close') or contains(@aria-label, 'Close')]",
        
        # Close buttons with × symbol
        "//button[contains(text(), '×')]",
        "//button[text()='×']",
        "//a[contains(text(), '×')]",
        "//span[contains(text(), '×')]/parent::button",
    ]

    # Try to close modals first
    for selector in modal_close_selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            for element in elements:
                if element.is_displayed():
                    try:
                        driver.execute_script("arguments[0].click();", element)
                        logger.info("✅ Closed modal/popup")
                        time.sleep(2)
                        break
                    except Exception:
                        continue
        except Exception:
            continue

    # Try to hide/remove overlay containers directly
    try:
        overlay_containers = [
            "mfp-container",
            "mfp-bg",
            "modal-backdrop",
            "overlay",
            "popup-overlay"
        ]
        
        for container_class in overlay_containers:
            elements = driver.find_elements(By.CLASS_NAME, container_class)
            for element in elements:
                try:
                    driver.execute_script("arguments[0].style.display = 'none';", element)
                    logger.info(f"✅ Hidden overlay container: {container_class}")
                except Exception:
                    continue
    except Exception:
        pass

    # Now handle cookie consent specifically
    consent_selectors = [
        # Button text-based selectors (German)
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'akzeptieren')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'alle akzeptieren')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'zustimmen')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'verstanden')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'einverstanden')]",
        
        # English
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept all')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ok')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow')]",
        
        # Class and ID-based selectors
        "//button[contains(@class, 'cookie')]",
        "//button[contains(@class, 'consent')]",
        "//button[contains(@id, 'cookie')]",
        "//button[contains(@id, 'consent')]",
        "//a[contains(@class, 'cookie')]",
        "//div[contains(@class, 'cookie')]//button",
        "//div[contains(@class, 'gdpr')]//button",
        "//div[contains(@class, 'privacy')]//button"
    ]

    # Try main page first
    for selector in consent_selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    # Try multiple click methods
                    try:
                        element.click()
                    except:
                        driver.execute_script("arguments[0].click();", element)
                    logger.info(f"✅ Clicked cookie consent button")
                    time.sleep(2)
                    return True
        except Exception:
            continue

    # Try in iframes
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for idx, iframe in enumerate(iframes):
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(iframe)
                
                for selector in consent_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                try:
                                    element.click()
                                except:
                                    driver.execute_script("arguments[0].click();", element)
                                logger.info(f"✅ Clicked cookie consent in iframe #{idx}")
                                driver.switch_to.default_content()
                                time.sleep(2)
                                return True
                    except Exception:
                        continue
                        
            except Exception:
                continue
            finally:
                driver.switch_to.default_content()
    except Exception:
        pass

    # Force remove any remaining overlays
    try:
        driver.execute_script("""
            // Remove all mfp containers
            document.querySelectorAll('.mfp-container, .mfp-bg, .mfp-wrap').forEach(el => el.remove());
            
            // Remove modal backdrops
            document.querySelectorAll('.modal-backdrop, .overlay, .popup-overlay').forEach(el => el.remove());
            
            // Remove any element with high z-index that might be blocking
            document.querySelectorAll('*').forEach(el => {
                const zIndex = window.getComputedStyle(el).zIndex;
                if (zIndex && parseInt(zIndex) > 9999) {
                    const display = window.getComputedStyle(el).display;
                    if (display !== 'none') {
                        el.style.display = 'none';
                    }
                }
            });
        """)
        logger.info("✅ Force removed overlay elements")
    except Exception as e:
        logger.warning(f"Could not force remove overlays: {e}")

    logger.info("Overlay and consent handling completed")
    return False


def fill_any_input_fields(driver, user_data):
    """Enhanced form filling with better field detection"""
    name = user_data.get("name", "")
    email = user_data.get("email", "")
    phone = user_data.get("phone", "")
    location = user_data.get("location", "")
    skills = user_data.get("skills", [])
    
    filled_any = False
    retry_count = 3

    for attempt in range(retry_count):
        try:
            # Find all form elements
            inputs = driver.find_elements(By.TAG_NAME, "input")
            selects = driver.find_elements(By.TAG_NAME, "select")
            textareas = driver.find_elements(By.TAG_NAME, "textarea")
            
            logger.info(f"Found {len(inputs)} inputs, {len(selects)} selects, {len(textareas)} textareas")

            # Fill input fields
            for input_element in inputs:
                try:
                    if not input_element.is_displayed() or not input_element.is_enabled():
                        continue

                    input_type = input_element.get_attribute("type") or ""
                    placeholder = (input_element.get_attribute("placeholder") or "").lower()
                    name_attr = (input_element.get_attribute("name") or "").lower()
                    id_attr = (input_element.get_attribute("id") or "").lower()
                    class_attr = (input_element.get_attribute("class") or "").lower()
                    
                    # Combine all attributes for matching
                    all_attrs = f"{placeholder} {name_attr} {id_attr} {class_attr}".lower()

                    # Skip hidden, submit, and button types
                    if input_type.lower() in ['hidden', 'submit', 'button', 'reset', 'image']:
                        continue

                    # Email field detection
                    if any(keyword in all_attrs for keyword in ['email', 'e-mail', 'mail']) or input_type == 'email':
                        safe_fill_field(driver, input_element, email, "email")
                        filled_any = True
                        
                    # Phone field detection
                    elif any(keyword in all_attrs for keyword in ['phone', 'tel', 'mobile', 'telephone']) or input_type == 'tel':
                        safe_fill_field(driver, input_element, phone, "phone")
                        filled_any = True
                        
                    # Name field detection
                    elif any(keyword in all_attrs for keyword in ['name', 'fullname', 'full_name', 'firstname', 'lastname', 'vorname', 'nachname']):
                        safe_fill_field(driver, input_element, name, "name")
                        filled_any = True
                        
                    # Location field detection
                    elif any(keyword in all_attrs for keyword in ['location', 'city', 'address', 'ort', 'stadt']):
                        safe_fill_field(driver, input_element, location, "location")
                        filled_any = True

                except StaleElementReferenceException:
                    logger.warning("Stale element encountered, retrying...")
                    break
                except Exception as e:
                    logger.warning(f"Could not fill input field: {e}")
                    continue

            # Fill textarea fields (for cover letters, additional info, etc.)
            for textarea in textareas:
                try:
                    if not textarea.is_displayed() or not textarea.is_enabled():
                        continue
                        
                    placeholder = (textarea.get_attribute("placeholder") or "").lower()
                    name_attr = (textarea.get_attribute("name") or "").lower()
                    
                    if any(keyword in f"{placeholder} {name_attr}" for keyword in ['message', 'cover', 'letter', 'additional', 'comment']):
                        cover_letter = f"Dear Hiring Manager,\n\nI am interested in this position. My skills include: {', '.join(skills[:5])}.\n\nBest regards,\n{name}"
                        safe_fill_field(driver, textarea, cover_letter, "cover letter")
                        filled_any = True
                        
                except Exception as e:
                    logger.warning(f"Could not fill textarea: {e}")
                    continue

            # If we successfully filled fields without stale element exception, break
            if filled_any:
                break

        except StaleElementReferenceException:
            logger.warning(f"Stale elements detected, retry {attempt + 1}/{retry_count}")
            time.sleep(1)
            continue
        except Exception as e:
            logger.error(f"Error in form filling attempt {attempt + 1}: {e}")
            break

    return filled_any


def safe_fill_field(driver, element, value, field_type):
    """Safely fill a form field with retry logic and overlay handling"""
    if not value:
        return False
        
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # First, try to remove any overlays that might be blocking
            if attempt > 0:  # Only on retries
                driver.execute_script("""
                    document.querySelectorAll('.mfp-container, .mfp-bg, .modal-backdrop').forEach(el => {
                        el.style.display = 'none';
                        el.remove();
                    });
                """)
                time.sleep(1)
            
            # Scroll element into view
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(1)
            
            # Wait for element to be clickable
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable(element))
            
            # Try JavaScript click first (more reliable for intercepted elements)
            driver.execute_script("arguments[0].focus();", element)
            time.sleep(0.5)
            
            # Clear existing content using multiple methods
            driver.execute_script("arguments[0].value = '';", element)
            element.clear()
            time.sleep(0.2)
            
            # Set value using JavaScript (most reliable)
            driver.execute_script("arguments[0].value = arguments[1];", element, value)
            
            # Also send keys to trigger events
            try:
                element.send_keys(Keys.CONTROL + "a")
                element.send_keys(value)
            except Exception:
                # If send_keys fails, at least we have JavaScript value
                pass
            
            # Trigger necessary events
            driver.execute_script("""
                arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                arguments[0].dispatchEvent(new Event('blur', {bubbles: true}));
            """, element)
            
            # Verify the value was set
            current_value = element.get_attribute('value')
            if current_value and value in current_value:
                logger.info(f"✅ Filled {field_type}: {value[:20]}...")
                return True
            else:
                logger.warning(f"Value verification failed for {field_type}, attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    continue
                    
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed for {field_type}: {e}")
            if "element click intercepted" in str(e) and attempt < max_retries - 1:
                # Handle click interception specifically
                logger.info("Handling click interception...")
                try:
                    # Try to click the intercepting element to close it
                    driver.execute_script("""
                        var intercepting = document.elementFromPoint(arguments[1], arguments[2]);
                        if (intercepting && intercepting !== arguments[0]) {
                            // Try to close it
                            var closeBtn = intercepting.querySelector('.close, .mfp-close, [aria-label*="close"]');
                            if (closeBtn) closeBtn.click();
                            else intercepting.style.display = 'none';
                        }
                    """, element, 500, 300)  # Check center of screen
                    time.sleep(1)
                    continue
                except:
                    pass
            
            if attempt == max_retries - 1:
                logger.error(f"Could not fill {field_type} after {max_retries} attempts: {e}")
                return False
                
    return False


def try_submit_form(driver):
    """Try to submit the form using various methods"""
    submit_selectors = [
        # German
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'bewerbung')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'senden')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'absenden')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'bewerben')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'jetzt bewerben')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'e-mail-benachrichtigung')]",
        
        # English
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply now')]",
        
        # French
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'postuler')]",
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'envoyer')]",
        
        # Generic selectors
        "//input[@type='submit']",
        "//button[@type='submit']",
        "//button[contains(@class, 'submit')]",
        "//button[contains(@class, 'apply')]"
    ]

    for selector in submit_selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    # Scroll to element
                    driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    time.sleep(1)
                    
                    # Click using JavaScript to avoid interception
                    driver.execute_script("arguments[0].click();", element)
                    logger.info("✅ Clicked submit button")
                    
                    # Wait for potential page change or confirmation
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.any_of(
                                EC.url_changes(driver.current_url),
                                EC.presence_of_element_located((By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'danke')]")),
                                EC.presence_of_element_located((By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'thank you')]")),
                                EC.presence_of_element_located((By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'merci')]")),
                                EC.presence_of_element_located((By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'success')]"))
                            )
                        )
                        logger.info("✅ Form submission confirmed!")
                        return True
                    except TimeoutException:
                        logger.info("Form submitted but no confirmation detected")
                        return True
                        
        except Exception as e:
            logger.warning(f"Could not click submit button: {e}")
            continue

    logger.warning("❌ Could not find or click any submit button")
    return False