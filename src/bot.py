import faulthandler
import json
import os
import pickle
import time

import xmltodict
from loguru import logger
from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from urlmatch import urlmatch
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from webdriver_manager.core.utils import ChromeType
from course import Course

faulthandler.enable()

WAIT_TIME = 5  # minutes

url = "https://simpleenroll.stanford.edu/SimpleEnroll/index"

login_url = "https://login.stanford.edu/idp/profile/SAML2/Redirect/SSO?execution=e1s2"
duo_security_domain = "https://*.duosecurity.com/frame/*"
duo_tmp_url = "https://api-531b0865.duosecurity.com/frame/v4/error?sid=frameless-1e197e52-fd22-4252-a56d-e3b15baf233a"

with open("credentials.json", "r") as f:
    credentials = json.load(f)

username = credentials["username"]
password = credentials["password"]

logger.remove()
# Primary logs
logger.add("logs/bot.log", rotation="1 week", level="DEBUG")


class Bot:
    def __init__(self, username, password):
        self.username = username
        self.password = password

        self.courses = []

        options = webdriver.ChromeOptions()
        options.add_argument("--headless")

        # Install the ChromeDriverManager locally
        service = Service(ChromeDriverManager(path=".chromedriver").install())
        self.driver = webdriver.Chrome(service=service, options=options)

    def get_courses(self):
        with open("src/js/get_course.js", "r") as f:
            js = f.read()

        enrolled_courses = self.driver.execute_script(
            js.replace("[CourseSetType]", "SE_EnrolledCourseSet"))
        planned_courses = self.driver.execute_script(
            js.replace("[CourseSetType]", "SE_PlannedCourseSet"))

        courses = enrolled_courses + planned_courses

        for course in courses:
            for c in self.courses:
                if c.id == course["id"]:
                    c.update(course)
                    break
            else:
                # If the course is not in the list, add it
                self.courses.append(Course(course))

        # We also need to remove courses that are no longer in the list
        for c in self.courses:
            if c.id not in [course["id"] for course in courses]:
                self.courses.remove(c)

    def batch_enroll(self):
        self.get_courses()
        self.print_course_table()
        self.set_status("Enrolling courses...")
        with open("src/js/batch_enroll.js", "r") as f:
            js = f.read()

        result = self.driver.execute_async_script(js)
        data = xmltodict.parse(result)

        errors = data.get("STF_SE", {}).get("Errors", [])
        parsed_errors = []

        for error in errors:
            if isinstance(error, dict):
                error_list = error.get("Error", [])

                for err in error_list:
                    subject = err.get("@Subject", "")
                    message = err.get("#text", "")
                    parsed_errors.append(
                        {"Subject": subject, "Message": message})

        # Find each course in planned_courses and update the error
        for course in self.courses:
            if not course.is_planned:
                continue
            subject = course.subject + " " + course.course_number
            for error in parsed_errors:
                if error["Subject"] == subject:
                    course.error = error["Message"].replace(
                        "<br>", "").split("\n")[0]

        self.driver.refresh()
        time.sleep(4)
        self.get_courses()

    def set_status(self, status, log=True):
        if log:
            logger.info(status)
        status_message = f"[green]Status:[/] {status}"
        status_panel = Panel(
            status_message, border_style="green", expand=True, padding=(0, 1))

        self.layout["status"].update(status_panel)

    def add_attempt(self, attempts):
        attempts += 1
        self.layout["attempts"].update(
            Panel(f"[green]Attempts:[/] {attempts}", border_style="green", expand=True, padding=(0, 1)))

        return attempts

    def print_course_table(self):
        table = Table(show_header=True, header_style="bold green",
                      padding=(0, 1), show_lines=True, expand=True)
        table.add_column("Course", justify="left", max_width=20)
        table.add_column("Time", justify="left")
        table.add_column("Status", justify="left")
        table.add_column("Info", justify="left", max_width=80)
       # Simulate getting all_courses (you should replace this with your actual logic)

        # Clear the table rows before adding updated data
        table.rows = []

        for course in sorted(self.courses, key=lambda x: x.name()):
            status = "✅ Enrolled" if course.status == "E" else "Not Enrolled"
            table.add_row(course.name(), course.get_time(), status, course.error)

        table_panel = Panel(table, border_style="green",
                            expand=True, padding=(0, 1))

        # Update the live display with the new table
        self.layout["table"].update(table_panel)

    def quit_program(self):
        self.set_status("[bold red]Quitting...[/bold red]")
        self.driver.quit()
        time.sleep(1)
        self.live.stop()
        exit(1)

    def run(self):
        layout = Layout(name="")
        status_layout = Layout(name="status_panel", size=3)
        status_layout.split_row(Layout(name="status"),
                                Layout(name="attempts"))
        layout.split(Layout(name="Title", size=3),
                     status_layout, Layout(name="table"))
        layout["Title"].update(
            Panel(Align("[bold green]SimpleEnroll Bot[/bold green]", "center"), expand=True, border_style="green"))
        layout["attempts"].update(
            Panel(f"[green]Attempts:[/] 0", border_style="green", expand=True, padding=(0, 1)))

        attempts = 0

        with Live(layout, refresh_per_second=6, screen=True) as live:
            try:
                self.live = live
                self.layout = layout
                self.set_status("Initializing...")
                self.print_course_table()
                if os.path.exists("data/duo_cookies.json"):
                    self.load_duo_cookies()
                    self.login(needs_duo=False)
                else:
                    self.login(needs_duo=True)

                time.sleep(3)
                self.get_courses()
                self.print_course_table()

                while True:

                    if not self.is_logged_in():
                        self.login()

                    time.sleep(2)
                    self.batch_enroll()
                    self.print_course_table()
                    attempts = self.add_attempt(attempts)
                    self.set_status("Waiting...")
                    # Custom wait print message update every 5 seconds
                    for i in range(0, int(WAIT_TIME * 60), 5):
                        self.set_status(
                            f"Waiting... {int(WAIT_TIME * 60) - i} seconds left")
                        time.sleep(5)

            except KeyboardInterrupt:
                self.quit_program()
            except Exception as e:
                logger.exception(e)
                self.quit_program()

    def login(self, needs_duo=False):
        self.set_status("Logging in...")
        self.driver.get(url)
        # If url is not login_url, then login
        if self.driver.current_url == url:
            return

        # Wait for url change
        current = self.driver.current_url
        self.driver.find_element("name", "username").send_keys(self.username)
        self.driver.find_element("name", "password").send_keys(self.password)
        self.driver.find_element("name", "_eventId_proceed").click()

        WebDriverWait(self.driver, 20).until(
            lambda d: d.current_url != current)

        if needs_duo:
            logger.info(self.driver.current_url + " " + duo_security_domain)
            if urlmatch(duo_security_domain, self.driver.current_url):
                current = self.driver.current_url
                logger.info("Duo security page loaded!")
                self.set_status("Waiting for 2fA.")
                # Wait for button with text "Yes, trust browser"
                WebDriverWait(self.driver, 40).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Yes, trust browser')]"))).click()

                # Wait for 2FA
                WebDriverWait(self.driver, 20).until(
                    lambda d: d.current_url != current)

                self.set_status("Saving Duo Security cookies...")
                # Go back to Duo Security page, it will b invalid, but whatev
                self.driver.get(current)
                cookies = self.driver.get_cookies()

                if not os.path.exists("data"):
                    os.makedirs("data")
                f = open("data/duo_cookies.json", "w+")
                json.dump(cookies, f)
                f.close()

                self.set_status("Saved Duo Security cookies!")
                self.driver.get(url)
        WebDriverWait(self.driver, 20).until(lambda d: d.current_url == url)
        self.set_status("Logged in!")

    def load_duo_cookies(self):
        self.set_status("Bypassing Duo Security...")
        self.driver.get(duo_tmp_url)
        cookies_path = "data/duo_cookies.json"
        with open(cookies_path, "r") as f:
            cookies = json.load(f)

        for cookie in cookies:
            if "sameSite" in cookie and cookie["sameSite"] not in ["Strict", "Lax", "None"]:
                del cookie["sameSite"]

            # if "domain" in cookie and cookie["domain"] in target_domain:
            #     self.driver.add_cookie(cookie)
            # elif "domain" not in cookie:
            #     self.driver.add_cookie(cookie)

            self.driver.add_cookie(cookie)

    def is_logged_in(self):
        self.driver.get(url)
        return self.driver.current_url == url


if __name__ == "__main__":
    bot = Bot(username, password)
    bot.run()
