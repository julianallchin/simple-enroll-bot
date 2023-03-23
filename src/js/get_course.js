const courses = [CourseSetType].prototype.courses;
return courses.map((c) => {
  return {
    id: c.psId,
    courseTitle: c.courseTitle,
    subject: c.subject,
    courseNum: c.courseNum,
    instructors: c.instructors,
    isPlanned: c.isPlanned,
    status: c.status,
    componentCode: c.componentCode,
    careerCode: c.careerCode,
    scheduleEntries: c.scheduleEntries.map((s) => {
      return {
        daysText: s.daysText,
        startDate: s.startDate,
        endDate: s.endDate,
        startTime: s.startTime,
        endTime: s.endTime,
        room: s.room,
      };
    }),
  };
});
