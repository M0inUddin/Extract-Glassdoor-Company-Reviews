import gradio as gr
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time
import os
from dotenv import load_dotenv
import random

# Load environment variables
load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s",
)


def setup_driver():
    logging.info("Setting up the WebDriver.")
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


def human_type(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.2))  # Random delay between keystrokes


def login_to_glassdoor(driver):
    logging.info("Navigating to Glassdoor and attempting to log in.")
    driver.get("https://www.glassdoor.com")
    time.sleep(5)  # Wait for the page to load

    # Find and fill the email field
    email_field = driver.find_element(By.CSS_SELECTOR, "input#inlineUserEmail")
    human_type(email_field, EMAIL)

    # Find and click the continue button
    continue_button = driver.find_element(
        By.CSS_SELECTOR, "button[data-test='email-form-button']"
    )
    continue_button.click()

    time.sleep(10)  # Wait for the password field to appear

    # Find and fill the password field
    password_field = driver.find_element(By.CSS_SELECTOR, "input#inlineUserPassword")
    human_type(password_field, PASSWORD)
    time.sleep(10)
    # Find and click the sign-in button
    sign_in_button = driver.find_element(
        By.CSS_SELECTOR, "button[class='Button Button']"
    )
    sign_in_button.click()

    time.sleep(10)  # Wait for the login process to complete
    logging.info("Logged in to Glassdoor successfully.")


def dismiss_overlays(driver):
    try:
        consent_button = driver.find_element(
            By.CSS_SELECTOR, "button#onetrust-accept-btn-handler"
        )
        if consent_button.is_displayed():
            consent_button.click()
            time.sleep(2)  # Wait for the overlay to disappear
            logging.info("Consent overlay dismissed.")
    except Exception as e:
        logging.error(f"Error dismissing overlay: {e}")


def scrape_data(driver, max_pages, url):
    logging.info(f"Scraping data from {url} for {max_pages} pages.")
    driver.execute_script(f"window.open('{url}', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    time.sleep(10)  # Wait for the page to load

    dismiss_overlays(driver)  # Dismiss any overlays if present

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

        logging.info(f"Scraped {len(reviews)} reviews from page {page_count + 1}.")

        try:
            next_button = driver.find_element(
                By.CSS_SELECTOR, 'button[data-test="next-page"]'
            )
            driver.execute_script("arguments[0].scrollIntoView();", next_button)
            next_button.click()
            page_count += 1
            time.sleep(5)  # Wait for the next page to load
        except Exception as e:
            logging.error(f"Error navigating to the next page: {e}")
            break

    logging.info("Data scraping completed.")
    return data


def save_to_csv(data, filename="reviews.csv"):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    logging.info(f"Data has been written to {filename}.")
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
        logging.info("WebDriver closed.")


interface = gr.Interface(
    fn=access_and_interact,
    inputs=["text", "number"],
    outputs=["text", "file"],
    title="Web Scraper Interface",
    description="Please Enter the URL of reviews page from Glassdoor.",
    allow_flagging="never",
)

interface.launch(server_name="0.0.0.0", server_port=7860, share=True)
