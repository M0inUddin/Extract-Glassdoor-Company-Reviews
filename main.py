import gradio as gr
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time

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

def scrape_data(driver, max_pages, url):
    # First open a tab to glassdoor.com
    driver.get("https://www.glassdoor.com")
    time.sleep(5)  # Wait for the page to load

    # Now open the user-provided URL in a new tab
    driver.execute_script(f"window.open('{url}', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    time.sleep(10)  # Wait for the page to load

    data = []
    page_count = 0
    while page_count < max_pages:
        time.sleep(3)
        reviews = driver.find_elements(By.CSS_SELECTOR, "div.review-details_topReview__5NRVX")
        for review in reviews:
            try:
                rating = review.find_element(By.CSS_SELECTOR, "span.review-details_overallRating__Rxhdr").text.strip()
            except Exception as e:
                rating = None
            try:
                date = review.find_element(By.CSS_SELECTOR, "span.timestamp_reviewDate__fBGY6").text.strip()
            except Exception as e:
                date = None
            try:
                title = review.find_element(By.CSS_SELECTOR, 'h2[data-test="review-details-title"]').text.strip()
            except Exception as e:
                title = None
            try:
                employee_role = review.find_element(By.CSS_SELECTOR, "span.review-details_employee__MeSp3").text.strip()
            except Exception as e:
                employee_role = None
            try:
                review_url = review.find_element(By.CSS_SELECTOR, 'a[data-test="review-details-title-link"]').get_attribute("href")
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
            next_button = driver.find_element(By.CSS_SELECTOR, 'button[data-test="next-page"]')
            if next_button.is_enabled():
                next_button.click()
                page_count += 1
                time.sleep(5)  # Wait for the next page to load
            else:
                break
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
        data = scrape_data(driver, int(max_pages), url)
        return save_to_csv(data)
    finally:
        driver.quit()

flagging_dir = "/home/ubuntu/flagged"  # Specify the directory for flagging
interface = gr.Interface(
    fn=access_and_interact,
    inputs=["text", "number"],
    outputs=["text", "file"],
    title="Web Scraper Interface",
    description="Enter the URL of the page and the number of pages to scrape.",
    flagging_dir=flagging_dir,  # Specify the flagging directory
)

interface.launch(server_name="0.0.0.0", server_port=7860)
