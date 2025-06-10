DEFAULT_PROMPT = """
Analyze the provided document(s) and extract all results related only to these indicators:
    • "Capacity Sharing for Development"
    • "Policy Change"

If no relevant information for either indicator is found, do not assume or invent data. Instead, return a JSON object with an empty array of results, like this:

{
    "results": []
}

⸻

Instructions for Each Identified Result

1. Indicator Type

Determine whether the result is one of the following:

Capacity Sharing for Development
    • Involves individual and group activities and engagement aimed at changing knowledge, attitudes, skills, or practices.
    • Capacity development refers to activities that develop the know-how and capacity to design, test, validate, and use innovations. These activities are considered instrumental in leading to behavioral changes in knowledge, attitude, skills, and practice among CGIAR and non-CGIAR personnel.
    • The main goal is to capture gender composition and the number of people trained long-term or short-term (including Masters' and PhD students) by Alliance staff.
    • Examples: training-of-trainers programs at the farmer level; providing guidance on RBM and MEL; training programs with public and private sector partners; educating PhD and MSc students; ongoing institutional support to national partners, particularly NARES; and decision support for policymakers.
    • Possible keywords: "capacity", "capacitated", "capacity sharing", "capacity building", "training", "trained", "trainee", "trainees", "trainer", "students", "workshop", "webinar", "in-person", "hybrid", "online", "attendance", "attended", "attendees", "sessions", "participation", "participants", "participated", "took part", "male", "female", "total", "male participants", "female participants", "men", "women", "learning", "facilitator", "mentor", "mentored", "instructor", "lecturer", "coach", "seminar", "conference", "e-learning", "program", "virtual", "engagement", "feedback", "skills", "skills development", "knowledge transfer", "learning", "supervisor", "capacity development", "programme", "degree", "masters", "university", "bachelor", "on-site".

Policy Change
    • Refers to the introduction or modification of policies, strategies, or regulations addressing specific issues.
    • Must show measurable impacts or outcomes aligned with the project/organization's goals.

⸻

2. General Information Fields

Result Title
    • title
    • Identify the exact title of the result as stated in the document.

Result Description
    • description
    • Provide a brief description of the result.

Keywords
    • keywords
    • List relevant keywords in lowercase, as an array of strings.

Geoscope (Geographical Scope)
    • geoscope
For each result, specify:
    • level:
        • "Global"
        • "Regional"
        • "National"
        • "Sub-national"
        • "This is yet to be determined"
    • sub_list:
        • If level = "Regional", return an array with the appropriate UN49 code(s).
        • If level = "National", return an array with the ISO Alpha-2 country code(s) (e.g., ["KE"]).
        • If level = "Sub-national", return an array of objects, each containing the country code and an array of subnational areas
            (e.g., [{"country_code": "KE", "areas": ["Western Kenya", "Eastern Kenya"]}]).
        • If not applicable, set "sub_list": null.

Alliance Main Contact Person
    • Extract and split the contact's name into the following fields:
        • alliance_main_contact_person_first_name
        • alliance_main_contact_person_last_name
    • Look for any mention or indication of the primary Alliance contact in the document (e.g., "Alliance focal point," "main Alliance contact," "Alliance coordinator," or a named person specifically flagged as responsible).
    • If no specific name or contact is mentioned, return:
        • alliance_main_contact_person_first_name: "Not collected"
        • alliance_main_contact_person_last_name: "Not collected"

⸻

3. Additional Requirements for "Capacity Sharing for Development"

Training Type
    • training_type
    • "Individual training"
    • "Group training"

For "Group training," validate and reinforce participant counting by ensuring:
    1. Extract participant lists
        If the document provides a full list of participants (e.g., in an appendix or table), use it to derive counts whenever possible.
    2. Use explicit participant counts
        If the document states explicit participant numbers (total, male, female, non_binary), use those values directly—unless there are contradictions.
    3. Partial gender counts
        • If only some gender counts are specified (e.g., male participants but not female or non_binary):
            • Fill in the known count for each gender.
            • For any missing genders, use "Not collected".
            • If total_participants is provided:
        • Ensure the sum of known gender counts matches total_participants. Use the following formula:
            total_participants = 
                (male_participants if explicitly stated in the document, else 0) + 
                (female_participants if explicitly stated in the document, else 0) + 
                (non_binary_participants if explicitly stated in the document, else 0)
        • If there is a discrepancy (e.g., total_participants is 15 but you can only account for 10 across known genders):
            • Keep the known gender counts.
            • Set any missing gender counts to "Not collected".
            • Adjust total_participants to reflect the sum of the known counts (in this example, 10). Do not invent additional participants.
        • If total_participants is not provided:
            • Record the known gender counts.
            • Set total_participants to "Not collected".
    4. Completely missing gender counts
        If total_participants is present but no gender-specific counts are given, assume:

        {
            "male_participants": "Not collected",
            "female_participants": "Not collected",
            "non_binary_participants": "Not collected"
        }

    5. Names with gender annotations
        If participant names are listed alongside gender details, count each individual accordingly:
        • Increase male_participants for males,
        • Increase female_participants for females,
        • Increase non_binary_participants if someone does not identify as male or female.
    6. Non-negative integer rule
        All participant counts must be non-negative integers (≥ 0). Use "Not collected" only when the document does not provide the necessary information.

Training Duration Validation
    • start_date and end_date should capture the training period as stated in the document (in YYYY-MM-DD format).
    • length_of_training should be calculated as the time elapsed between the start_date and the end_date.
    • If either date is missing, return "Not collected" for the start_date, end_date, and length_of_training.
    • Long-term training refers to training that goes for 3 or more months.
    • Short-term training refers to training that goes for less than 3 months.
    • If the document does not provide enough detail, use "Not collected".

Degree Validation (only if length_of_training is Long-term):
    • Only include the "degree" field **if and only if** length_of_training is "Long-term".
    • If length_of_training is not "Long-term", **do not include the "degree" field at all** in the output JSON.
    • When included, check if the document explicitly mentions that the training led to a degree such as:
        • "PhD"
        • "MSc"
        • "BSc"
        • "Other" (for any degree not classified under the above)
    • If a degree is mentioned, return its value.
    • If not specified, return "Not collected".

Delivery Modality
    • delivery_modality
    • If the document explicitly states how the training was delivered (e.g., "virtual," "in-person," "hybrid"), use that exact term.
    • If not stated, use "Not collected".

⸻
4. Additional Requirements for "Policy Change"

Policy Type
    • policy_type
    • Must be one of the following predefined values:
        • "Policy or Strategy"
        • "Legal instrument"
        • "Program, Budget, or Investment"
    • If the document does not explicitly state the type, return "Not collected".

Stage in Policy Process
    • stage_in_policy_process
    • Must be one of the following predefined stages:
        • "Stage 1: Research taken up by next user, policy change not yet enacted."
        • "Stage 2: Policy enacted."
        • "Stage 3: Evidence of impact of policy."
    • If only the stage ID is provided (e.g., "Stage 2"), map it to the full label above.
    • If the stage is unclear or not mentioned, return "Not collected".

Evidence for Stage
    • evidence_for_stage
    • Provide a brief textual explanation (maximum 200 words) describing how the policy stage is supported by the information in the document.
    • If no evidence is available, return "Not collected".

⸻
5. Output Format

Your output must be valid JSON and must not include any additional text or explanations.
Return dates in YYYY-MM-DD format or "Not collected".
For partial or missing participant data, follow the partial participant rule above.
Your output must be a single valid JSON object, and must not include any additional text, comments, footnotes, citations, or explanations.
Do not:
• Add text before or after the JSON.
• Add any explanatory sentences, notes, or references (e.g., "This result is extracted from…").
• Include markdown code blocks like ```json or ```.
The response must be raw JSON only — nothing else.

⸻
Follow this exact structure:

{
    "results": [
        {
            "indicator": "<'Capacity Sharing for Development' or 'Policy Change'>",
            "title": "<result title>",
            "description": "<result description>",
            "keywords": [
                "<keyword1>",
                "<keyword2>",
                "..."
            ],
            "geoscope": {
                "level": "<Global | Regional | National | Sub-national | This is yet to be determined>",
                "sub_list": <[array of codes or region names] or null>
            },
            "training_type": "<Individual training or Group training (only if applicable and indicator is 'Capacity Sharing for Development')>",
            "total_participants": <number or 'Not collected' (only if group training and indicator is 'Capacity Sharing for Development')>,
            "male_participants": <number or 'Not collected' (only if group training and indicator is 'Capacity Sharing for Development')>,
            "female_participants": <number or 'Not collected' (only if group training and indicator is 'Capacity Sharing for Development')>,
            "non_binary_participants": <number or 'Not collected' (only if group training and indicator is 'Capacity Sharing for Development')>,
            "delivery_modality": "<value or 'Not collected' (only if indicator is 'Capacity Sharing for Development')>",
            "start_date": "<value or 'Not collected' (only if indicator is 'Capacity Sharing for Development')>",
            "end_date": "<value or 'Not collected' (only if indicator is 'Capacity Sharing for Development')>",
            "length_of_training": "<Short-term or Long-term or 'Not collected' (only if indicator is 'Capacity Sharing for Development')>",
            "degree": "<value or 'Not collected' (only if length_of_training is Long-term and indicator is 'Capacity Sharing for Development')>",
            "alliance_main_contact_person_first_name": "<value or 'Not collected'>",
            "alliance_main_contact_person_last_name": "<value or 'Not collected'>",
            "evidence_for_stage": "<value or 'Not collected' (only if indicator is 'Policy Change')>",
            "policy_type": "<'Policy or Strategy' | 'Legal instrument' | 'Program, Budget, or Investment' | 'Not collected' (only if indicator is 'Policy Change')>",
            "stage_in_policy_process": "<Stage 1: ... | Stage 2: ... | Stage 3: ... | Not collected (only if indicator is 'Policy Change')>"
        }
    ]
}
"""