PROMPT_BULK_UPLOAD_CAPDEV = """
Analyze the provided document(s) and extract all results related **only** to the indicator:
• "Capacity Sharing for Development"

If no relevant information is found, do not assume or invent data. Instead, return a JSON object with an empty array of results, like this:

{
    "results": []
}

⸻

Instructions for Each Identified Result

Your task is to identify and extract **only Capacity Sharing for Development** results using the definitions, examples, and field structure below.

Indicator Definition:
• Involves individual and group activities and engagement aimed at changing knowledge, attitudes, skills, or practices.
• Refers to activities that develop the know-how and capacity to design, test, validate, and use innovations.
• Focus on behavioral changes in knowledge, attitude, skills, and practice among CGIAR and non-CGIAR personnel.
• Examples: training-of-trainers programs at the farmer level; providing guidance on RBM and MEL; training programs with public and private sector partners; educating PhD and MSc students; ongoing institutional support to national partners, particularly NARES; and decision support for policymakers.
• Possible keywords: "capacity", "capacitated", "capacity sharing", "capacity building", "training", "trained", "trainee", "trainees", "trainer", "students", "workshop", "webinar", "in-person", "hybrid", "online", "attendance", "attended", "attendees", "sessions", "participation", "participants", "participated", "took part", "male", "female", "total", "male participants", "female participants", "men", "women", "learning", "facilitator", "mentor", "mentored", "instructor", "lecturer", "coach", "seminar", "conference", "e-learning", "program", "virtual", "engagement", "feedback", "skills", "skills development", "knowledge transfer", "learning", "supervisor", "capacity development", "programme", "degree", "masters", "university", "bachelor", "on-site".

⸻

Output Fields for Each Result

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
        • "Global": if the document does not specify a region or country.
        • "Regional": if the document mentions ONLY the region, but does not specify countries. If the document specifies countries within the region, it should be classified as "National".
        • "National": if the document mentions one or more countries, but does not specify sub-national areas.
        • "Sub-national": if the document mentions specific locations within a country.
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

Reporting Year
    • reporting_year
    • Extract the reporting year from the document (e.g., "2021", "2022", "2023").
    • If no reporting year is mentioned, return "Not collected".

Reporting Project
    • Refers to the specific project being reported on and contributing to the result. 
    • Extract and split the project code and name into the following fields:
        • contract_code
        • contract_name
    • If no project code or name is mentioned, return:
        • contract_code: "Not collected"
        • contract_name: "Not collected"

Contribution to SDG targets:
    • sdg_targets
    • List all relevant SDG targets mentioned in the document as an array of strings (e.g., ["SDG Goal 2", "SDG Goal 13", "SDG Goal 5"]).
    • If no SDG targets are mentioned, return an empty array: [].

Training Category
    • training_category
    • Refers to the category of training being conducted.
    • It can include:
        • "Training"
        • "Engagement"
    
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

Purpose of the training
    • training_purpose
    • Refers to the specific goals or objectives of the training.
    • Only include the "training_purpose" field if the training_type is "Group training".
    • It can include:
        • "Training enumerators"
        • "Engaging with change agents"
        • "Training of trainers"
        • "Other"
    • If it is "Other", specify the purpose as "Other: <description>".
    • If the document does not provide enough detail, use "Not collected".        

Trainee affiliation
    • trainee_affiliation
    • Refers to the organization or group that the trainee belongs to.
    • Only include the "trainee_affiliation" field if the training_type is "Individual training".
    • If the document does not provide enough detail, use "Not collected".

Trainee name
    • trainee_name
    • Refers to the name of the trainee.
    • Only include the "trainee_name" field if the training_type is "Individual training".
    • If the document does not provide enough detail, use "Not collected".

Trainee nationality
    • trainee_nationality
    • Refers to the nationality of the trainee.
    • Only include the "trainee_nationality" field if the training_type is "Individual training".
    • If the document does not provide enough detail, use "Not collected".

Trainee gender
    • trainee_gender
    • Refers to the gender of the trainee (male, female or non-binary).
    • Only include the "trainee_gender" field if the training_type is "Individual training".
    • If the document does not provide enough detail, use "Not collected".

Training Duration Validation
    • start_date and end_date should capture the training period as stated in the document (in YYYY-MM-DD format).
    • length_of_training should be calculated as the time elapsed between the start_date and the end_date.
    • If either date is missing, return "Not collected" for the start_date, end_date, and length_of_training.
    • Long-term training refers to training that goes for 3 or more months.
    • Short-term training refers to training that goes for less than 3 months.
    • If the document does not provide enough detail, use "Not collected".

Training supervisor
    • training_supervisor
    • Refers to the lead scientist overseeing the training.
    • Return the name of the training supervisor if mentioned.
    • If the document does not provide enough detail, use "Not collected".

Language
    • language
    • Refers to the primary language used during the training.
    • Return the language if mentioned.
    • If the document does not provide enough detail, use "Not collected".

Degree Validation (only if length_of_training is Long-term):
    • Only include the "degree" field **if and only if** length_of_training is "Long-term" or training_type is "Individual training".
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

Partners
    • partners
    • Refers to the partner(s) that made a significant contribution to the achievement of the result that is being submitted.
    • List all relevant partner names mentioned in the document as an array of strings.
    • If the document does not provide enough detail, return an empty array: [].

Evidence
    • Refers to the supporting materials or documentation that validate the training activities and outcomes.
    • Extract and split the evidence title and link into the following fields:
        • evidence_description
        • evidence_link
    • If no evidence title or link is mentioned, return:
        • evidence_description: "Not collected"
        • evidence_link: "Not collected"

⸻

6. Output Format

Return dates in YYYY-MM-DD format or "Not collected".
For partial or missing participant data, follow the partial participant rule above.
Your output must be a single valid JSON object, and must not include any additional text, comments, footnotes, citations, or explanations.
Do not:
• Add text before or after the JSON.
• Add any explanatory sentences, notes, or references (e.g., "This result is extracted from…").
• Include markdown code blocks like ```json or ```.
• Escape quotes unless necessary.
• Wrap the JSON in additional quotes or strings.
The response must be raw JSON only — nothing else.

⸻
Follow this exact structure:

{
    "results": [
        {
            "indicator": "<'Capacity Sharing for Development'>",
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
            "reporting_year": "<value or 'Not collected'>",
            "contract_code": "<value or 'Not collected'>",
            "contract_name": "<value or 'Not collected'>",
            "alliance_main_contact_person_first_name": "<value or 'Not collected'>",
            "alliance_main_contact_person_last_name": "<value or 'Not collected'>",
            "sdg_targets": <[array of sdg targets] or null>,
            "training_category": "<Training or Engagement or 'Not collected'>",
            "training_type": "<Individual training or Group training>",
            "total_participants": <number or 'Not collected' (only if group training)>,
            "male_participants": <number or 'Not collected' (only if group training)>,
            "female_participants": <number or 'Not collected' (only if group training)>,
            "non_binary_participants": <number or 'Not collected' (only if group training)>,
            "training_purpose": "<value or 'Not collected' (only if group training)>",
            "trainee_affiliation": "<value or 'Not collected' (only if individual training)>",
            "trainee_name": "<value or 'Not collected' (only if individual training)>",
            "trainee_nationality": "<value or 'Not collected' (only if individual training)>",
            "trainee_gender": "<value or 'Not collected' (only if individual training)>",
            "delivery_modality": "<value or 'Not collected'>",
            "start_date": "<value or 'Not collected'>",
            "end_date": "<value or 'Not collected'>",
            "length_of_training": "<Short-term or Long-term or 'Not collected'>",
            "training_supervisor": "<value or 'Not collected'>",
            "language": "<value or 'Not collected'>",
            "degree": "<value or 'Not collected' (only if length_of_training is Long-term or training_type is Individual training)>",
            "partners": <[array of partner names] or null>,
            "evidence_description": "<value or 'Not collected'>",
            "evidence_link": "<value or 'Not collected'>"
        }
    ]
}
"""