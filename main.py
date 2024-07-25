import gradio as gr
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time
import os


def setup_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def close_popups(driver):
    try:
        popup_close_button = driver.find_element(
            By.CSS_SELECTOR, "button.popup-close-button"
        )  # Update selector to match actual popup close button
        if popup_close_button.is_displayed():
            popup_close_button.click()
            time.sleep(2)  # Wait for the popup to close
    except Exception as e:
        pass


def login_to_glassdoor(driver):
    driver.get("https://www.glassdoor.com")
    time.sleep(5)  # Wait for the page to load

    close_popups(driver)  # Close any popups if present

    # Find and fill the email field
    email_field = driver.find_element(By.CSS_SELECTOR, "input#inlineUserEmail")
    email_field.send_keys(os.environ.get("EMAIL"))

    # Find and click the continue button
    continue_button = driver.find_element(
        By.CSS_SELECTOR, "button[data-test='email-form-button']"
    )
    continue_button.click()

    time.sleep(10)  # Wait for the password field to appear

    close_popups(driver)  # Close any popups if present

    # Find and fill the password field
    password_field = driver.find_element(By.CSS_SELECTOR, "input#inlineUserPassword")
    password_field.send_keys(os.environ.get("PASSWORD"))
    time.sleep(10)
    # Find and click the sign-in button
    sign_in_button = driver.find_element(
        By.CSS_SELECTOR, "button[class='Button Button']"
    )
    sign_in_button.click()

    time.sleep(10)  # Wait for the login process to complete
    close_popups(driver)  # Close any popups if present


def dismiss_overlays(driver):
    try:
        consent_button = driver.find_element(
            By.CSS_SELECTOR, "button#onetrust-accept-btn-handler"
        )
        if consent_button.is_displayed():
            consent_button.click()
            time.sleep(2)  # Wait for the overlay to disappear
    except Exception as e:
        pass


def scrape_data(driver, max_pages, url):
    # Now open the user-provided URL in a new tab
    driver.execute_script(f"window.open('{url}', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    time.sleep(10)  # Wait for the page to load

    dismiss_overlays(driver)  # Dismiss any overlays if present
    close_popups(driver)  # Close any popups if present

    data = []
    page_count = 0
    while page_count < max_pages:
        time.sleep(3)
        reviews = driver.find_elements(
            By.CSS_SELECTOR, "div.review-details_topReview__5NRVX"
        )
        for review in reviews:
            try:
                rating = review.find_element(
                    By.CSS_SELECTOR, "span.review-details_overallRating__Rxhdr"
                ).text.strip()
            except Exception as e:
                rating = None
            try:
                date = review.find_element(
                    By.CSS_SELECTOR, "span.timestamp_reviewDate__fBGY6"
                ).text.strip()
            except Exception as e:
                date = None
            try:
                title = review.find_element(
                    By.CSS_SELECTOR, 'h2[data-test="review-details-title"]'
                ).text.strip()
            except Exception as e:
                title = None
            try:
                employee_role = review.find_element(
                    By.CSS_SELECTOR, "span.review-details_employee__MeSp3"
                ).text.strip()
            except Exception as e:
                employee_role = None
            try:
                review_url = review.find_element(
                    By.CSS_SELECTOR, 'a[data-test="review-details-title-link"]'
                ).get_attribute("href")
            except Exception as e:
                review_url = None

            data.append(
                {
                    "Rating": rating,
                    "Date": date,
                    "Title": title,
                    "Employee Role": employee_role,
                    "URL": review_url,
                }
            )

        try:
            next_button = driver.find_element(
                By.CSS_SELECTOR, 'button[data-test="next-page"]'
            )
            driver.execute_script("arguments[0].scrollIntoView();", next_button)
            next_button.click()
            page_count += 1
            time.sleep(5)  # Wait for the next page to load
        except Exception as e:
            break

    return data


def save_to_csv(data, filename="reviews.csv"):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    return f"Data has been written to {filename}", filename


def access_and_interact(url, max_pages):
    driver = setup_driver()
    try:
        login_to_glassdoor(driver)
        time.sleep(10)  # Wait for the login process to complete
        data = scrape_data(driver, int(max_pages), url)
        return save_to_csv(data)
    finally:
        driver.quit()


interface = gr.Interface(
    fn=access_and_interact,
    inputs=["text", "number"],
    outputs=["text", "file"],
    title="Web Scraper Interface",
    description="Please Enter the URL of reviews page from Glassdoor.",
    allow_flagging="never",
)

interface.launch(server_name="0.0.0.0", server_port=7860)
