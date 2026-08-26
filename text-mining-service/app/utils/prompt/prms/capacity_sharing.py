CAPACITY_SHARING_SECTION = """
⸻

Additional Requirements for "Capacity Sharing for Development"

Indicator definition:
    • Involves individual and group activities and engagement aimed at changing knowledge, attitudes, skills, or practices.
    • Capacity development refers to activities that develop the know-how and capacity to design, test, validate, and use innovations.
    • In PRMS this is an Output — it reports formal capacity-sharing activities (training, workshops, degree programs, institutional support) rather than informal knowledge exchange alone.
    • Examples: training-of-trainers programs at the farmer level; providing guidance on RBM and MEL; training programs with public and private sector partners; educating PhD and MSc students; ongoing institutional support to national partners, particularly NARES; and decision support for policymakers.
    • Possible keywords: "capacity", "capacitated", "capacity sharing", "capacity building", "training", "trained", "trainee", "trainees", "trainer", "students", "workshop", "webinar", "in-person", "hybrid", "online", "attendance", "attended", "attendees", "sessions", "participation", "participants", "participated", "took part", "male", "female", "total", "male participants", "female participants", "men", "women", "learning", "facilitator", "mentor", "mentored", "instructor", "lecturer", "coach", "seminar", "conference", "e-learning", "program", "virtual", "engagement", "feedback", "skills", "skills development", "knowledge transfer", "learning", "supervisor", "capacity development", "programme", "degree", "masters", "university", "bachelor", "on-site".

Type-specific block: capacity_sharing (object, required for this indicator when type-specific data exists)

number_people_trained (object inside capacity_sharing)
    • Report counts by gender when stated in sources.
    • Fields: women, men, non_binary, unknown — each a non-negative integer.
    • Include at least one gender count field when participant numbers are known.
    • Do not invent counts; omit missing gender fields rather than guessing.
    • If sources give total only without gender split, use unknown or omit gender fields except the total implied count in unknown if explicitly stated as undifferentiated.
    • If sources provide a full list of participants with or without gender, derive counts from the list.
    • Partial gender counts: include only supported fields; do not fabricate the rest.

length_training (string enum inside capacity_sharing)
    • Refers to the duration of the training or capacity building activity.
    • Must be one of the following predefined values:
        • "Short-term" — training under 3 months (workshops, short courses).
        • "Long-term" — training 3 months or longer.
    • Omit if not supported by sources.

delivery_method (string enum inside capacity_sharing)
    • Refers to the method used to deliver the training or capacity building activity.
    • Must be one of the following predefined values:
        • "Virtual / Online"
        • "In person"
        • "Blended (in-person and virtual)"
    • If the document does not explicitly state the method, do not return the delivery_method field in the output JSON.

Example:
{
    "capacity_sharing": {
        "number_people_trained": {"women": 25, "men": 18, "non_binary": 0, "unknown": 10},
        "length_training": "Short-term",
        "delivery_method": "Blended (in-person and virtual)"
    }
}
"""
