# Import the necessary modules
import faulthandler
import json
import os
import time

import xmltodict
from loguru import logger
from rich.align import Align
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from urlmatch import urlmatch
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType

# Import the Course class from course.py file
from course import Course

# Enable fault handler to catch fatal errors in Python scripts
faulthandler.enable()

# Define a constant for the wait time between each enrollment attempt (in minutes)
WAIT_TIME = 5

# Define the URL for the SimpleEnroll website
url = "https://simpleenroll.stanford.edu/SimpleEnroll/index"

# Define the URL for the Stanford login page
login_url = "https://login.stanford.edu/idp/profile/SAML2/Redirect/SSO?execution=e1s2"

# Define the domain for the Duo Security page
duo_security_domain = "https://*.duosecurity.com/frame/*"

# Define a temporary URL for the Duo Security page (used to load cookies)
duo_tmp_url = "https://api-531b0865.duosecurity.com/frame/v4/error?sid=frameless-1e197e52-fd22-4252-a56d-e3b15baf233a"

# Load the credentials from a JSON file
with open("credentials.json", "r") as f:
    credentials = json.load(f)

username = credentials["username"]
password = credentials["password"]

# Configure the logger to write to a file with rotation and level options
logger.remove()
logger.add("logs/bot.log", rotation="1 week", level="DEBUG")


class Bot:
    def __init__(self, username, password):
        # Initialize the bot with the given username and password
        self.username = username
        self.password = password

        # Initialize an empty list of courses to enroll in
        self.courses = []

        # Initialize the Chrome options for headless mode (no GUI)
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")

        # Install the ChromeDriverManager locally and create a webdriver instance with the options
        service = Service(ChromeDriverManager(path=".chromedriver").install())
        self.driver = webdriver.Chrome(service=service, options=options)

    def get_courses(self):
        # Get the list of enrolled and planned courses from the website using a JavaScript script

        # Read the JavaScript script from a file and replace [CourseSetType] with the appropriate value
        with open("src/js/get_course.js", "r") as f:
            js = f.read()

        # Execute the script and get the results as a list of dictionaries for each course type
        enrolled_courses = self.driver.execute_script(
            js.replace("[CourseSetType]", "SE_EnrolledCourseSet"))
        planned_courses = self.driver.execute_script(
            js.replace("[CourseSetType]", "SE_PlannedCourseSet"))

        # Combine the two lists into one list of courses
        courses = enrolled_courses + planned_courses

        # For each course in the list, check if it is already in self.courses and update it if so, or add it if not.
        for course in courses:
            for c in self.courses:
                if c.id == course["id"]:
                    c.update(course)
                    break
            else:
                # If the course is not in the list, add it as a Course object
                self.courses.append(Course(course))

        # We also need to remove courses that are no longer in the list by comparing their ids.
        for c in self.courses:
            if c.id not in [course["id"] for course in courses]:
                self.courses.remove(c)

    def batch_enroll(self):
        # Enroll in all planned courses using a JavaScript script

        # Get the updated list of courses from the website first.
        self.get_courses()

        # Print the current course table to show their status and info.
        self.print_course_table()

        # Set the status message to indicate that enrollment is in progress.
        self.set_status("Enrolling courses...")

        # Read the JavaScript script from a file that performs batch enrollment.
        with open("src/js/batch_enroll.js", "r") as f:
            js = f.read()

        # Execute the script asynchronously and get the result as an XML string.
        result = self.driver.execute_async_script(js)

        # Parse the XML string into a dictionary using xmltodict module.
        data = xmltodict.parse(result)

        # Get the list of errors from the dictionary, if any.
        errors = data.get("STF_SE", {}).get("Errors", [])
        parsed_errors = []

        # For each error in the list, extract the subject and message fields and store them in a new list of dictionaries.
        for error in errors:
            if isinstance(error, dict):
                error_list = error.get("Error", [])

                for err in error_list:
                    subject = err.get("@Subject", "")
                    message = err.get("#text", "")
                    parsed_errors.append(
                        {"Subject": subject, "Message": message})

        # Find each course in planned_courses and update the error attribute with the corresponding message from parsed_errors.
        for course in self.courses:
            if not course.is_planned:
                continue
            subject = course.subject + " " + course.course_number
            for error in parsed_errors:
                if error["Subject"] == subject:
                    course.error = error["Message"].replace(
                        "<br>", "").split("\n")[0]

        # Refresh the driver to update the website state.
        self.driver.refresh()
        time.sleep(4)

        # Get the updated list of courses from the website again.
        self.get_courses()

    def set_status(self, status, log=True):
        # Set the status message to be displayed on the live console and optionally log it to a file.

        if log:
            logger.info(status)

        # Format the status message with green color and add it to a panel.
        status_message = f"[green]Status:[/] {status}"
        status_panel = Panel(
            status_message, border_style="green", expand=True, padding=(0, 1))

        # Update the status layout with the new panel.
        self.layout["status"].update(status_panel)

    def add_attempt(self, attempts):
        # Increment the number of attempts and update the attempts layout with a new panel.

        attempts += 1
        self.layout["attempts"].update(
            Panel(f"[green]Attempts:[/] {attempts}", border_style="green", expand=True, padding=(0, 1)))

        return attempts

    def print_course_table(self):
        # Print a table of courses with their names, times, statuses and info on the live console.

        # Create a table object with headers and styles using rich module.
        table = Table(show_header=True, header_style="bold green",
                      padding=(0, 1), show_lines=True, expand=True)
        table.add_column("Course", justify="left", max_width=20)
        table.add_column("Time", justify="left")
        table.add_column("Status", justify="left")
        table.add_column("Info", justify="left", max_width=80)

        # Clear the table rows before adding updated data
        table.rows = []

        # For each course in self.courses (sorted by name), add a row with its name, time, status and info.
        for course in sorted(self.courses, key=lambda x: x.name()):
            status = "✅ Enrolled" if course.status == "E" else "Not Enrolled"
            table.add_row(course.name(), course.get_time(),
                          status, course.error)

        # Add the table to a panel and update the table layout with it.
        table_panel = Panel(table, border_style="green",
                            expand=True, padding=(0, 1))
        self.layout["table"].update(table_panel)

    def quit_program(self):
        # Quit the program gracefully by closing the driver and stopping the live console.

        self.set_status("[bold red]Quitting...[/bold red]")
        self.driver.quit()
        time.sleep(1)
        self.live.stop()
        exit(1)

    def run(self):
        # Run the main loop of the bot.

        # Create a layout object with sub-layouts for title, status, attempts and table using rich module.
        layout = Layout(name="")
        status_layout = Layout(name="status_panel", size=3)
        status_layout.split_row(Layout(name="status"),
                                Layout(name="attempts"))
        layout.split(Layout(name="Title", size=3),
                     status_layout, Layout(name="table"))

        # Add a panel with a title to the title layout.
        layout["Title"].update(
            Panel(Align("[bold green]SimpleEnroll Bot[/bold green]", "center"), expand=True, border_style="green"))

        # Add a panel with the initial number of attempts to the attempts layout.
        layout["attempts"].update(
            Panel(f"[green]Attempts:[/] 0", border_style="green", expand=True, padding=(0, 1)))

        # Initialize the number of attempts to zero.
        attempts = 0

        # Create a live object with the layout and refresh rate using rich module.
        with Live(layout, refresh_per_second=6, screen=True) as live:
            try:
                # Store the live object and the layout object as attributes of the bot for easy access.
                self.live = live
                self.layout = layout

                # Set the initial status message to indicate that the bot is initializing.
                self.set_status("Initializing...")

                # Print an empty course table to show the layout.
                self.print_course_table()

                # Check if there is a file with Duo Security cookies and load them if so, or login normally if not.
                if os.path.exists("data/duo_cookies.json"):
                    self.load_duo_cookies()
                    self.login(needs_duo=False)
                else:
                    self.login(needs_duo=True)

                # Wait for 3 seconds to let the website load completely.
                time.sleep(3)

                # Get the list of courses from the website and print them on the table.
                self.get_courses()
                self.print_course_table()

                # Start an infinite loop that tries to enroll in planned courses every WAIT_TIME minutes.
                while True:

                    # Check if the bot is still logged in by visiting the SimpleEnroll URL and comparing it with the current URL.
                    if not self.is_logged_in():
                        # If not logged in, login again.
                        self.login()

                    # Wait for 2 seconds to let the website load completely.
                    time.sleep(2)

                    # Try to enroll in planned courses using batch enrollment and print the updated course table.
                    self.batch_enroll()
                    self.print_course_table()

                    # Increment the number of attempts and update the attempts layout with it.
                    attempts = self.add_attempt(attempts)

                    # Set the status message to indicate that the bot is waiting for the next attempt.
                    self.set_status("Waiting...")

                    # Wait for WAIT_TIME minutes and update the status message every 5 seconds to show how much time is left.
                    for i in range(0, int(WAIT_TIME * 60), 5):
                        self.set_status(
                            f"Waiting... {int(WAIT_TIME * 60) - i} seconds left")
                        time.sleep(5)

            except KeyboardInterrupt:
                # If the user presses Ctrl+C, quit the program gracefully.
                self.quit_program()
            except Exception as e:
                # If any other exception occurs, log it to a file and quit the program gracefully.
                logger.exception(e)
                self.quit_program()

    def login(self, needs_duo=False):
        # Login to the SimpleEnroll website using username and password.

        # Set the status message to indicate that login is in progress.
        self.set_status("Logging in...")

        # Visit the SimpleEnroll URL using the driver.
        self.driver.get(url)

        # If the current URL is already equal to SimpleEnroll URL, then return as login is not needed.
        if self.driver.current_url == url:
            return

        # Wait for the URL to change after entering username and password and clicking on proceed button.
        current = self.driver.current_url
        self.driver.find_element("name", "username").send_keys(self.username)
        self.driver.find_element("name", "password").send_keys(self.password)
        self.driver.find_element("name", "_eventId_proceed").click()

        WebDriverWait(self.driver, 20).until(
            lambda d: d.current_url != current)

        if needs_duo:
            # If Duo Security page is needed, check if the current URL matches its domain using urlmatch module.
            logger.info(self.driver.current_url + " " + duo_security_domain)
            if urlmatch(duo_security_domain, self.driver.current_url):
                current = self.driver.current_url
                logger.info("Duo security page loaded!")

                # Set the status message to indicate that 2FA is needed and wait for it.
                self.set_status("Waiting for 2fA.")

                # Wait for button with text "Yes, trust browser" to be clickable and click on it.
                WebDriverWait(self.driver, 40).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Yes, trust browser')]"))).click()

                # Wait for 2FA to complete and the URL to change.
                WebDriverWait(self.driver, 20).until(
                    lambda d: d.current_url != current)

                # Set the status message to indicate that Duo Security cookies are being saved.
                self.set_status("Saving Duo Security cookies...")

                # Go back to Duo Security page, it will be invalid, but it doesn't matter.
                self.driver.get(current)

                # Get the cookies from the driver and save them to a JSON file for future use.
                cookies = self.driver.get_cookies()

                if not os.path.exists("data"):
                    os.makedirs("data")
                f = open("data/duo_cookies.json", "w+")
                json.dump(cookies, f)
                f.close()

                # Set the status message to indicate that Duo Security cookies are saved.
                self.set_status("Saved Duo Security cookies!")

                # Go back to SimpleEnroll URL using the driver.
                self.driver.get(url)

        # Wait for the current URL to be equal to SimpleEnroll URL using WebDriverWait.
        WebDriverWait(self.driver, 20).until(lambda d: d.current_url == url)

        # Set the status message to indicate that login is successful.
        self.set_status("Logged in!")

    def load_duo_cookies(self):
        # Load the Duo Security cookies from a JSON file and add them to the driver.

        # Set the status message to indicate that Duo Security is being bypassed using cookies.
        self.set_status("Bypassing Duo Security...")

        # Visit the temporary Duo Security URL using the driver.
        self.driver.get(duo_tmp_url)

        # Load the cookies from the JSON file using json module.
        cookies_path = "data/duo_cookies.json"
        with open(cookies_path, "r") as f:
            cookies = json.load(f)

        # For each cookie in the list, check and remove the sameSite attribute if it is not valid and add it to the driver.
        for cookie in cookies:
            if "sameSite" in cookie and cookie["sameSite"] not in ["Strict", "Lax", "None"]:
                del cookie["sameSite"]

            self.driver.add_cookie(cookie)

    def is_logged_in(self):
        # Check if the bot is still logged in by visiting the SimpleEnroll URL and comparing it with the current URL.

        # Visit the SimpleEnroll URL using the driver.
        self.driver.get(url)

        # Return True if the current URL is equal to SimpleEnroll URL, False otherwise.
        return self.driver.current_url == url


if __name__ == "__main__":
    # Create a bot instance with username and password and run it.
    bot = Bot(username, password)
    bot.run()
