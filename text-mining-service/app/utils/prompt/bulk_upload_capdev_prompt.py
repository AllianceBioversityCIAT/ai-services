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

Record ID (Internal Use Only)
    • id
    • Extract the ID value from the document (e.g., from an "ID" column in the Excel file).
    • This ID should correspond to the identifier already present in the source document.
    • This field is REQUIRED and must be included in every result.
    • If the document doesn't have an explicit ID column, do not return this field in the output JSON.

Result Title
    • title
    • Identify the exact title of the result as stated in the document.
    • If no title is mentioned explicitly, try to infer a concise title that accurately reflects the content of the result.

Result Description
    • description
    • Provide a brief description of the result.

Reporting Year
    • year
    • Extract the reporting year from the document (e.g., "2021", "2022", "2023").
    • If no reporting year is mentioned, do not return the year field in the output JSON.    

Alliance Main Contact Person
    • Extract the contact's name into the following field as an object:
        • main_contact_person: {"name": "..."}
    • Look for any mention or indication of the primary Alliance contact in the document (e.g., "Alliance focal point," "main Alliance contact," "Alliance coordinator," or a named person specifically flagged as responsible).
    • It could be also the person who reported the result.
    • If no specific name or contact is mentioned, do not return the field in the output JSON.

Keywords
    • keywords
    • List relevant keywords in lowercase, as an array of strings.

Reporting Project
    • Refers to the specific project being reported on and contributing to the result. 
    • Extract the project code into the following field:
        • contract_code
    • If no project code is mentioned, return an empty string in the output JSON.

Contribution to SDG targets:
    • sdg_targets
    • List all relevant SDG targets mentioned in the document as an array of strings (e.g., ["SDG2", "SDG13", "SDG5"]).
    • Make sure to include the "SDG" prefix followed by the target number (e.g., "SDG1", "SDG2", ..., "SDG17").
    • If no SDG targets are mentioned, do not return the sdg_targets field in the output JSON.

Training Category
    • training_category
    • Refers to the category of training being conducted.
    • It can include:
        • "Training"
        • "Engagement"
    • If the document does not provide enough detail, do not return the training_category field in the output JSON.

Training Duration Validation
    • start_date and end_date should capture the training period as stated in the document (in YYYY-MM-DD format).
    • length_of_training should be calculated as the time elapsed between the start_date and the end_date.
    • Long-term training refers to training that goes for 3 or more months.
    • Short-term training refers to training that goes for less than 3 months.
    • If the document does not provide enough detail about the training duration or dates, do not return the missing field(s) in the output JSON.

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
            • For any missing genders, do not return the field in the output JSON.
            • If total_participants is provided:
        • Ensure the sum of known gender counts matches total_participants. Use the following formula:
            total_participants = 
                (male_participants if explicitly stated in the document, else 0) + 
                (female_participants if explicitly stated in the document, else 0) + 
                (non_binary_participants if explicitly stated in the document, else 0)
        • If there is a discrepancy (e.g., total_participants is 15 but you can only account for 10 across known genders):
            • Keep the known gender counts.
            • Set any missing gender counts to null (do not return the field in the output JSON).
            • Adjust total_participants to reflect the sum of the known counts (in this example, 10). Do not invent additional participants.
        • If total_participants is not provided:
            • Record the known gender counts.
            • Set total_participants to null (do not return the field in the output JSON).
    4. Completely missing gender counts
        If total_participants is present but no gender-specific counts are given, assume:

        {
            "male_participants": null (do not return the field in the output JSON),
            "female_participants": null (do not return the field in the output JSON),
            "non_binary_participants": null (do not return the field in the output JSON)
        }

    5. Names with gender annotations
        If participant names are listed alongside gender details, count each individual accordingly:
        • Increase male_participants for males,
        • Increase female_participants for females,
        • Increase non_binary_participants if someone does not identify as male or female.
    6. Non-negative integer rule
        All participant counts must be non-negative integers (≥ 0). Use null only when the document does not provide the necessary information.

Purpose of the training
    • training_purpose
    • Refers to the specific goals or objectives of the training.
    • Only include the "training_purpose" field if the training_type is "Group training".
    • It can include:
        • "Training enumerators"
        • "Engaging with change agents"
        • "Training of trainers"
        • "Other"
    • If it is "Other", specify the purpose as "Other: <purpose description>".
    • If the document does not provide enough detail, do not return the training_purpose field in the output JSON.

Trainees Organizations
    • trainees
    • Only include this field if the training_type is "Group training".
    • Refers to whether the trainees were attending the training on behalf of an organization.
    • Return "Yes" if there is clear evidence that trainees represent specific organizations.
    • Return "No" if there is no evidence or mention of organizational representation.
    • IMPORTANT: For Group training, you should ALWAYS return either "Yes" or "No" - do NOT omit this field unless it's impossible to determine.
    • If you cannot determine with reasonable confidence, default to "No".
    
    • trainees_description
    • Only include this field if trainees is "Yes" and training_type is "Group training".
    • Refers to the organizations that the training attendees represent or belong to.
    • IMPORTANT: Do not confuse with partners. Trainees organizations are represented BY the attendees at the training, while partners contribute TO the training.
    • List all relevant organization names mentioned in the document as an array of objects with the following structure:
        [{"institution_name": "<institution name 1>"}, {"institution_name": "<institution name 2>"}]
    • If there are multiple organizations, they will be separated by commas, and you should list each one as a separate object in the array.
    • If the document does not provide enough detail, do not return the trainees_description field in the output JSON.

Degree Validation:
    • Only include the "degree" field **if and only if** length_of_training is "Long-term" or training_type is "Individual training".
    • If length_of_training is not "Long-term", **do not include the "degree" field at all** in the output JSON.
    • When included, check if the document explicitly mentions that the training led to a degree such as:
        • "PhD"
        • "MSc"
        • "BSc"
        • "Other" (for any degree not classified under the above)
    • If a degree is mentioned, return its value.
    • If not specified, do not return the degree field in the output JSON.

Trainee affiliation
    • trainee_affiliation
    • Refers to the organization or group that the trainee belongs to.
    • Only include the "trainee_affiliation" field if the training_type is "Individual training".
    • Return this field as an object with the following structure:
        {"institution_name": "<name of the affiliation>"}
    • If the document does not provide enough detail, do not return the trainee_affiliation field in the output JSON.

Trainee name
    • trainee_name
    • Refers to the name of the trainee.
    • Only include the "trainee_name" field if the training_type is "Individual training".
    • If the document does not provide enough detail, do not return the trainee_name field in the output JSON.

Trainee nationality
    • trainee_nationality
    • Refers to the nationality of the trainee.
    • Only include the "trainee_nationality" field if the training_type is "Individual training".
    • Return this field as an object with the following structure:
        {"code": "<ISO Alpha-2 country code>"}
        e.g. {"code": "KE"} for Kenya, {"code": "IN"} for India.
    • If the document does not provide enough detail, do not return the trainee_nationality field in the output JSON.

Trainee gender
    • trainee_gender
    • Refers to the gender of the trainee (male, female or non-binary).
    • Only include the "trainee_gender" field if the training_type is "Individual training".
    • If the document does not provide enough detail, do not return the trainee_gender field in the output JSON.

Training supervisor
    • training_supervisor
    • Refers to the lead scientist overseeing the training.
    • Do not confuse with the Alliance main contact person, unless it is explicitly stated that the primary Alliance contact is also the training supervisor.
    • Return the name of the training supervisor as an object:
        {"name": "<name of the training supervisor>"}
    • If the document does not provide enough detail, do not return the training_supervisor field in the output JSON.

Language
    • language
    • Refers to the primary language used during the training.
    • Return the language if mentioned as an object:
        {"name": "<language name>", "code": "<ISO Alpha-3 code of the language>"}
    • Use your knowledge of ISO Alpha-3 language codes to provide the appropriate code based on the language name mentioned in the document.
    • If the document does not provide enough detail, do not return the language field in the output JSON.

Delivery Modality
    • delivery_modality
    • If the document explicitly states how the training was delivered (e.g., "virtual," "in-person," "hybrid"), use that exact term.
    • If not stated, do not return the delivery_modality field in the output JSON.

Partners
    • partners
    • Refers to the partner(s) that made a significant contribution to the achievement of the result that is being submitted.
    • These are organizations that contribute to, support, or collaborate in conducting the training or capacity building activity.
    • IMPORTANT: Do not confuse with trainees organizations. Partners contribute TO the training, while trainees organizations are represented BY the attendees.
    • List all relevant partner names mentioned in the document as an array of objects with the following structure:
        [{"institution_name": "<institution name 1>"}, {"institution_name": "<institution name 2>"}]
    • If there are multiple partners, they will be separated by commas, and you should list each one as a separate object in the array.
    • If the document does not provide enough detail, do not return the partners field in the output JSON.

Geoscope (Geographical Scope)
    • For each result, specify:
        • geoscope_level:
            • "Global": if the document does not specify a region or country.
            • "Regional": if the document mentions ONLY the region, but does not specify countries. If the document specifies countries within the region, it should be classified as "National".
            • "National": if the document mentions one or more countries, but does not specify sub-national areas.
            • "Sub-national": if the document mentions specific locations within a country.
            • "This is yet to be determined"
        • regions and countries:
            • If level = "Regional", return an array with the appropriate UN49 region code(s) as numbers:
                (e.g., regions: [150, 2] (150 for Europe region and 2 for Africa region)).
            • If level = "National", return an array with objects containing the ISO Alpha-2 country code(s):
                (e.g., countries: [{"code": "KE"}, {"code": "UG"}]).
            • If level = "Sub-national", return an array of objects, each containing the country code and an array with the appropriate ISO 3166-2 code(s) for the subnational areas. 
              Use your knowledge of ISO 3166-2 subnational codes to provide the appropriate codes based on the location names mentioned in the document:
                (e.g., countries: [{"code": "CO", "areas": ["CO-CUN", "CO-CAS"]}]).
            • If not applicable, do not return the regions or countries field in the output JSON.
    
Evidence
    • Refers to the supporting materials or documentation that validate the training activities and outcomes.
    • Extract the evidence(s) description and link into the following field as an array of objects:
        • evidences: [{"evidence_description": "<evidence description>", "evidence_link": "<URL>"}]
    • Only include the evidence field if BOTH the evidence_description AND evidence_link are present for a given evidence.
    • If either the description or the link is missing for any evidence, do not include that evidence object in the array.
    • If no evidence objects meet this requirement, do not return the evidence field in the output JSON.

Intellectual Property Rights
    • asset_ip_owner_id
        • Refers to who owns the intellectual property rights to this asset.
        • Look for information related to asset ownership or intellectual property ownership in the document.
        • Return as a numeric value (1, 2, 3, or 4) corresponding to:
            • 1: "International Center for Tropical Agriculture - CIAT"
            • 2: "Bioversity International"
            • 3: "Bioversity International and International Center for Tropical Agriculture - CIAT"
            • 4: "Others"
        • If the document does not provide enough detail, do not return the asset_ip_owner_id field in the output JSON.
    
    • asset_ip_owner_description
        • Only include this field if asset_ip_owner_id is 4.
        • Extract the specific name or description of the owner from the document.
        • If the document does not provide enough detail, do not return the asset_ip_owner_description field in the output JSON.
    
    • publicity_restriction
        • Refers to whether there are any legal restrictions for the publication of the work (confidential information or embargo periods).
        • Return "Yes" or "No" based on information found in the document regarding legal restrictions or publication limitations.
        • If the document does not provide enough detail, do not return the publicity_restriction field in the output JSON.
    
    • publicity_restriction_description
        • Only include this field if publicity_restriction is "Yes".
        • Extract and provide details about the legal restrictions, confidential information, or embargo periods mentioned in the document.
        • If the document does not provide enough detail, do not return the publicity_restriction_description field in the output JSON.
    
    • potential_asset
        • Refers to whether there is any potential for commercialization, release, or making available this asset.
        • Return "Yes" or "No" based on information found in the document regarding commercialization potential or asset availability.
        • If the document does not provide enough detail, do not return the potential_asset field in the output JSON.
    
    • potential_asset_description
        • Only include this field if potential_asset is "Yes".
        • Extract and provide details about the commercialization potential, release plans, or availability mentioned in the document.
        • If the document does not provide enough detail, do not return the potential_asset_description field in the output JSON.
    
    • requires_further_development
        • Refers to whether this asset requires further development or refinement.
        • Return "Yes" or "No" based on information found in the document regarding the need for additional development or refinement.
        • If the document does not provide enough detail, do not return the requires_further_development field in the output JSON.
    
    • requires_further_development_description
        • Only include this field if requires_further_development is "Yes".
        • Extract and provide details about what further development or refinement is needed as mentioned in the document.
        • If the document does not provide enough detail, do not return the requires_further_development_description field in the output JSON.

⸻

6. Output Format

Return dates in YYYY-MM-DD format when available.
For partial or missing participant data, follow the partial participant rule above.
Your output must be a single valid JSON object, and must not include any additional text, comments, footnotes, citations, or explanations.

**IMPORTANT: Only include fields in the JSON when information is found in the document or inferred by you. Do not include fields with null values or missing information - simply omit them entirely from the output.**

Required and mandatory fields:
• id
• indicator
• title
• description
• year
• keywords
• contract_code
• training_type
• training_category
• geoscope_level

Do not:
• Add text before or after the JSON.
• Add any explanatory sentences, notes, or references (e.g., "This result is extracted from…").
• Include markdown code blocks like ```json or ```.
• Escape quotes unless necessary.
• Wrap the JSON in additional quotes or strings.
• Return values like "null", "N/A", "unknown", "not specified" or something similar for missing fields.
• Include fields with null values - omit them completely.
The response must be raw JSON only — nothing else.

⸻
Follow this exact structure:

{
    "results": [
        {
            "id": "<numeric value (as extracted from the document)>",
            "indicator": "<'Capacity Sharing for Development'>",
            "title": "<result title>",
            "description": "<result description>",
            "year": "<value>",
            "main_contact_person": {
                "name": "<value>"
            },
            "keywords": [
                "<keyword1>",
                "<keyword2>",
                "..."
            ],
            "contract_code": "<value>",
            "sdg_targets": <[array of sdg targets]>,
            "training_category": "<Training or Engagement>",
            "start_date": "<value>",
            "end_date": "<value>",
            "length_of_training": "<Short-term or Long-term>",
            "training_type": "<Individual training or Group training>",
            "total_participants": <number (only if group training)>,
            "male_participants": <number (only if group training)>,
            "female_participants": <number (only if group training)>,
            "non_binary_participants": <number (only if group training)>,
            "training_purpose": "<value (only if group training)>",
            "trainees": "<Yes or No (only if group training)>",
            "trainees_description": [
                {
                    "institution_name": "<organization name 1>"
                },
                {
                    "institution_name": "<organization name 2>"
                },
                ...
            ] (only if trainees is Yes and training_type is Group training),
            "degree": "<value (only if length_of_training is Long-term or training_type is Individual training)>",
            "trainee_affiliation": {
                "institution_name": "<value (only if individual training)>"
            },
            "trainee_name": "<value (only if individual training)>",
            "trainee_nationality": {
                "code": "<ISO Alpha-2 value (only if individual training)>"
            },
            "trainee_gender": "<value (only if individual training)>",
            "training_supervisor": {
                "name": "<value>"
            },
            "language": {
                "name": "<value>",
                "code": "<ISO Alpha-3 value>"
            },
            "delivery_modality": "<value>",
            "partners": [
                {
                    "institution_name": "<partner name 1>"
                },
                {
                    "institution_name": "<partner name 2>"
                },
                ...
            ],
            "geoscope_level": "<Global | Regional | National | Sub-national | This is yet to be determined>",
            "regions": [<UN49 region code 1>, <UN49 region code 2>, ...] (only if geoscope_level is Regional),
            "countries": [
                {
                    "code": "<ISO Alpha-2 country code (if geoscope_level is National or Sub-national)>",
                    "areas": ["<ISO 3166-2 subnational area code 1>", "<ISO 3166-2 subnational area code 2>"] (only if geoscope_level is Sub-national)
                }
            ] (only if geoscope_level is National or Sub-national),
            "evidences": [
                {
                    "evidence_description": "<value>",
                    "evidence_link": "<value>"
                }
            ],
            "asset_ip_owner_id": <numeric value (1, 2, 3, or 4)>,
            "asset_ip_owner_description": "<value (only if asset_ip_owner_id is 4)>",
            "publicity_restriction": "<Yes or No>",
            "publicity_restriction_description": "<value (only if publicity_restriction is Yes)>",
            "potential_asset": "<Yes or No>",
            "potential_asset_description": "<value (only if potential_asset is Yes)>",
            "requires_further_development": "<Yes or No>",
            "requires_further_development_description": "<value (only if requires_further_development is Yes)>"
        }
    ]
}
"""