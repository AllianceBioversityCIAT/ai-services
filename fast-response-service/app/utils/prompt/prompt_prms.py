DEFAULT_PROMPT_PRMS = """
Analyze the provided document(s) and extract all results related only to these indicators:
    • "Capacity Sharing for Development"
    • "Policy Change"
    • "Innovation Development"

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

Innovation Development
    • Refers to a new, improved, or adapted output or groups of outputs such as technologies, products and services, policies, and other organizational and institutional arrangements with high potential to contribute to positive impacts when used at scale.  

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

5. Additional Requirements for "Innovation Development"

Short Title:
    • short_title
    • Provide a short name that facilitates clear communication about the innovation for a non-specialist reader and without acronyms. No more than 10 words.

Innovation Nature:
    • innovation_nature
    • Must be one of the following predefined values:
        • "Incremental innovation": Innovations that already exist and undergo constant, steady progress, and improvement.
        • "Radical innovation": Innovations that are new and replace existing products, systems, services and/or policies but do not cause or require major reconfiguration of farming, market and/or policy/ business models.
        • "Disruptive innovation": Innovations that are new and cause or require major reconfiguration of farming, market and/or policy/ business models.
        • "Other": Unknown or the characterization does not work for the innovation.
    • If the document does not specify the nature of the innovation, or it cannot be deduced, return "Other".
    • If the document provides a specific nature, use that value.

Innovation Type:
    • innovation_type
    • Must be one of the following predefined values:
        • "Technological innovation": Innovations of technical/ material nature, including varieties/ breeds; crop and livestock management practices; machines; processing technologies; big data and information systems.
        • "Capacity development innovation": Innovations that strengthen capacity, including farmer, extension or investor decision-support services; accelerator/ incubator programs; manuals, training programs and curricula; online courses.
        • "Policy/organizational/institutional innovation": Innovations that create enabling conditions, including policy, legal and regulatory frameworks; business models; finance mechanisms; partnership models; public/ private delivery strategies.
        • "Other": Unknown or the type does not work for the innovation.
    • If the document does not specify the type of innovation, or it cannot be deduced, return "Other".
    • If the document provides a specific type, use that value.

How would you assess the current readiness of this innovation?
    • assess_readiness
    • At the output level, a single readiness score is given for the innovation, irrespective of the specific geo-location where the innovation is being designed, tested and/or scaled. If you need help, use the Scaling Readiness Calculator for guidance.
    • This is the Scaling Readiness Calculator:
        • Level 0: Idea - The innovation is at idea stage.
        • Level 1: Basic Research - The innovation's basic principles are being researched for their ability to achieve a specific impact.
        • Level 2: Formulation - The innovation's key concepts are being formulated or designed.
        • Level 3: Proof of Concept - The innovation's key concepts have been validated for their ability to achieve a specific impact.
        • Level 4: Controlled Testing - The innovation is being tested for its ability to achieve a specific impact under fully-controlled conditions.
        • Level 5: Model/Early Prototype - The innovation is validated for its ability to achieve a specific impact under fully-controlled conditions.
        • Level 6: Semi-Controlled Testing - The innovation is being tested for its ability to achieve a specific impact under semi-controlled conditions.
        • Level 7: Prototype - The innovation is validated for its ability to achieve a specific impact under semi-controlled conditions.
        • Level 8: Uncontrolled Testing - The innovation is being tested for its ability to achieve a specific impact under uncontrolled conditions.
        • Level 9: Proven Innovation - The innovation is validated for its ability to achieve a specific impact under uncontrolled conditions.
    • Must be defined as a number between 0 and 9. Just use the number, not the description.
    • If the document does not specify the readiness level, or it cannot be deduced, return "Not collected".
    • If the document provides a specific readiness level, use that value.
    • If the document provides a description of the readiness level, map it to the corresponding number based on the Scaling Readiness Calculator.
    • If the document provides multiple readiness levels, use the highest level mentioned. For example, if it is level 7 in Kenya, level 3 in Peru and level 5 in India, only the highest score for the generic rank is retained.

Who would be the anticipated user(s) of this innovation?
    • anticipated_users
    • Must be one of the following predefined values:
        • "This is yet to be determined": If the document does not specify the users or it cannot be deduced.
        • "Users have been determined": If the document specifies or implies any direct or potential users of the innovation.
    • ONLY INCLUDE individuals or organizations that are direct or potential users or beneficiaries of the innovation — those who apply, adopt, or benefit from it. 
    • DO NOT INCLUDE funders, donors, implementing partners, or supporting organizations unless they are also users.
    • If at least one actor is mentioned in the document that fits this definition, select "Users have been determined" and extract the relevant actor(s) under innovation_actors.

Actors involved in the innovation:
    • innovation_actors_detailed
    • This field is used ONLY if the anticipated_users is "Users have been determined".
    • Do not include organizations, this field is only for individual actors.
    • Include the names, types, genres and ages of all individuals mentioned in the document that are potential or actual users or beneficiaries of the innovation.
    • Return a list of objects. Each object must include:
        • name: Full name of the actor, or "Not collected" if only the role or type is known.
        • type: Must be one or more of the following predefined values:
            • "Farmers / (agro)pastoralist / herders / fishers"
            • "Researchers"
            • "Extension agents"
            • "Policy actors (public or private)"
            • "Other"
        • other_actor_type: If the type is "Other", this field must contain information about the type of actor involved in the innovation that does not fit into the predefined values. If the type is not "Other", this field should not be included in the output JSON.
        • gender_age: Must be a single value or an array with one or more of the following predefined values, which defines the gender and age of the actor:
            • "Women: Youth"
            • "Women: Non-youth"
            • "Men: Youth"
            • "Men: Non-youth"
    • For gender_age, use the following definitions:
        • Youth = 15 to 24 years old
        • Non-youth = older than 24
    • If the document provides gender but not age:
        • Return both youth and non-youth for that gender (e.g., ["Women: Youth", "Women: Non-youth"])
    • If the document provides age but not gender:
        • Return both genders for that age group (e.g., ["Men: Youth", "Women: Youth"])
    • Do NOT create multiple entries for the same actor with different gender/age combinations.
    • If the document does not provide enough information, you may include partial entries (e.g., name and type only).
    • If anticipated_users is "This is yet to be determined", do not include this field in the output JSON.

Organization(s) involved in the innovation:
    • organizations
    • This field is used ONLY if the anticipated_users is "Users have been determined".
    • Include the names of all organizations mentioned in the document that are potential or actual users or beneficiaries of the innovation. These names were extracted from the anticipated_users field.
    • Do not include individuals, this field is only for organizations.
    • This field supports the classification of the organization_type, which is the only actor-related information displayed in the application interface.
    • If anticipated_users is "This is yet to be determined", do not include this field in the output JSON.

Organization types:
    • organization_type
    • This field is used ONLY if the anticipated_users is "Users have been determined".
    • This field is used to classify the type of organization(s) identified in the organizations field.
    • Must be one or more of the following predefined values:
        • "NGO"
        • "Research organizations and universities"
        • "Organization (other than financial or research)"
        • "Government"
        • "Financial institution"
        • "Private company (other than financial)"
        • "Public-Private Partnership"
        • "Foundation"
        • "Other"
    • If anticipated_users is "This is yet to be determined", do not include this field in the output JSON.

Organization sub-types:
    • organization_sub_type
    • This field is used ONLY if the organization_type is "NGO" or "Research organizations and universities" or "Organization (other than financial or research)" or "Government" or "Financial Institution".
    • If the organization_type is "Private company (other than financial)", "Public-Private Partnership", "Foundation", or "Other", this field should not be included in the output JSON.
    • If you have multiple organization types, you must include the organization_sub_type for each one.
    • If you do not know the sub-type, return "Not collected".
    • If the organization_type is "NGO", it must be one of the following predefined values:
        • NGO International
        • NGO International (General)
        • NGO International (Farmers)
        • NGO Regional
        • NGO Regional (General)
        • NGO Regional (Farmers)
        • NGO National
        • NGO National (General)
        • NGO National (Farmers)
        • NGO Local
        • NGO Local (General)
        • NGO Local (Farmers)
    • If the organization_type is "Research organizations and universities", it must be one of the following predefined values:
        • Research organizations and universities International
        • Research organizations and universities International (General)
        • Research organizations and universities International (Universities)
        • Research organizations and universities International (CGIAR)
        • Research organizations and universities Regional
        • Research organizations and universities Regional (NA)
        • Research organizations and universities Regional (Universities)
        • Research organizations and universities National
        • Research organizations and universities National (NARS)
        • Research organizations and universities National (Universities)
        • Research organizations and universities Local
        • Research organizations and universities Local (NA)
        • Research organizations and universities Local (Universities)
    • If the organization_type is "Organization (other than financial or research)", it must be one of the following predefined values:
        • Organization (other than financial or research) International
        • Organization (other than financial or research) Regional
    • If the organization_type is "Government", it must be one of the following predefined values:
        • Government (National)
        • Government (Subnational)
    • If the organization_type is "Financial institution", it must be one of the following predefined values:
        • Financial Institution
        • Financial Institution International
        • Financial Institution Regional
        • Financial Institution National
        • Financial Institution Local

Other organization types:
    • other_organization_type
    • This field is used ONLY if the organization_type is "Other".
    • If the organization_type is not "Other", this field should not be included in the output JSON.
    • This field should contain information about the type of organization involved in the innovation that does not fit into the predefined values.

⸻

6. Output Format

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
            "indicator": "<'Capacity Sharing for Development' or 'Policy Change' or 'Innovation Development'>",
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
            "short_title": "<value (only if indicator is 'Innovation Development')>",
            "innovation_nature": "<value or 'Other' (only if indicator is 'Innovation Development')>",
            "innovation_type": "<value or 'Other' (only if indicator is 'Innovation Development')>",
            "assess_readiness": "<number between 0 and 9 or 'Not collected' (only if indicator is 'Innovation Development')>",
            "anticipated_users": "<This is yet to be determined | Users have been determined (only if indicator is 'Innovation Development')>",
            "innovation_actors_detailed": [
                {
                    "name": "<actor name or 'Not collected' (only if anticipated_users is 'Users have been determined' and indicator is 'Innovation Development')>",
                    "type": "<value or 'Other' (only if anticipated_users is 'Users have been determined' and indicator is 'Innovation Development')>",
                    "other_actor_type": "<value or 'Not collected' (only if type is 'Other' and indicator is 'Innovation Development')>",
                    "gender_age:": "<value(s) or 'Not collected' (only if indicator is 'Innovation Development')>"
                }
            ],
            "organizations": "<array of organization names or 'Not collected' (only if anticipated_users is 'Users have been determined' and indicator is 'Innovation Development')>",
            "organization_type": "<value(s) or 'Other' (only if anticipated_users is 'Users have been determined' and indicator is 'Innovation Development')>",
            "organization_sub_type": "<value or 'Not collected' (only if indicator is 'Innovation Development')>",
            "other_organization_type": "<value or 'Not collected' (only if organization_type is 'Other' and indicator is 'Innovation Development')>"
        }
    ]
}
"""