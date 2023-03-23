class ScheduleEntry:
    def __init__(self, obj):
        self.days_text = obj["daysText"]
        self.start_date = obj["startDate"]
        self.end_date = obj["endDate"]
        self.start_time = obj["startTime"]
        self.end_time = obj["endTime"]
        self.room = obj["room"]

    def __str__(self):
        return f"{self.days_text} {self.start_time} - {self.end_time} {self.room}"

    def __repr__(self):
        return f"{self.days_text} {self.start_time} - {self.end_time} {self.room}"


class Course:
    def __init__(self, obj):
        self.id = obj["id"]
        self.course_title = obj["courseTitle"]
        self.subject = obj["subject"]
        self.course_number = obj["courseNum"]
        self.instructors = obj["instructors"]
        self.is_planned = obj["isPlanned"]
        self.status = obj["status"]
        self.component_code = obj["componentCode"]
        self.career_code = obj["careerCode"]
        self.schedule_entries = [ScheduleEntry(
            entry) for entry in obj["scheduleEntries"]]
        self.error = None

    def update(self, obj):
        self.id = obj["id"]
        self.course_title = obj["courseTitle"]
        self.subject = obj["subject"]
        self.course_number = obj["courseNum"]
        self.instructors = obj["instructors"]
        self.is_planned = obj["isPlanned"]
        self.status = obj["status"]
        self.component_code = obj["componentCode"]
        self.career_code = obj["careerCode"]
        self.schedule_entries = [ScheduleEntry(
            entry) for entry in obj["scheduleEntries"]]

    def name(self):
        return f"{self.subject} {self.course_number}"

    def __str__(self):
        return f"{self.course_title} {self.course_number}"

    def __repr__(self):
        return f"{self.course_title} {self.course_number}"
