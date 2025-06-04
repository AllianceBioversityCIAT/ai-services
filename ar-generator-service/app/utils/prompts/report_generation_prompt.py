PROMPT = """
# Role & Task Definition:
You are tasked with generating the narrative text for IPI 1.1: Climate-relevant knowledge products, decision-making tools and advisory services created or enhanced, including GSI dimensions (Number)​

## Objective:
Your goal is to craft a cohesive, structured, and data-driven narrative that highlights how “Beneficiaries with enhanced resilience to climate risks (Number).” (IPI 1.1).

---
Having into account this meausures to put in the Overall Numerical Summary:

[Total Target] = 93
[Total_Achieved] = 138

[Percentage] = Calculate(138/93)

---
## You have two JSON data sources available:

### IPI_1.1_Contributions.json:
Contains data on the achievements and contributions of various clusters under IPI 1.1: Climate-relevant knowledge products, decision-making tools and advisory services created or enhanced, including GSI dimensions (Number)​. Each entry includes:

        Cluster (Region or Thematic Area)
        Targeted number of partners (Target_year_by_PMC)
        Actual number of partners achieved (End_year_achieved)
        Achieved_narrative: A detailed explanation of how CIS and CSA access has improved, including new partnerships, policy changes, training      programs, digital tools, and innovations.

### IPI_1.1_Additional_question.json:
	Contains responses to four questions related to IPI 1.1, which tracks about Beneficiaries with enhanced resilience to climate risks 

It includes details on:
1. Reference the knowledge products listed in the main narrative that are expected to be gender-sensitive and explain  how gender considerations are dealt with (e.g. 1- Gender-responsive infographic on pesticide use- examples tailored to women crop and schedule; 2-....)
2. Reference the knowledge products listed in the main narrative that are expected to address other social inclusion dimensions, and explain how those issues are dealt with. (e.g. 1 - Socially-equitable agro-advisory app- visualization  options for those with impaired vision: 2- ....)
3. Reference  the knowledge products listed in the main narrative that are expected to be led by a regional partner PPAs (AGRHYMET, ASARECA, CCARDESA, CORAF, ICPAC, and RUFORUM)
4. Reference  the knowledge products listed in the main narrative that are expected to be "just-in-time" or driven by parter requests. Explain how the knowledge products are expected to contribute to a change (e.g. policy, straregy, plans, capacity, innovation use, investments).
Note: Number and name the knowledge products/ decision making tools and advisory services expected to be reported this year end (e.g. 1- Policy brief on CoP for pastoralist; 2- Infonote on pesticide use; 3-..)


---
## Introduction/Overview:
    
Clearly state the indicator and its purpose.

## Overall Numerical Summary:
	Provide a narrative that includes the overall target, the overall achieved number, and the achievement 	percentage (e.g., “By the end of 2024, 	AICCRA targeted the of 	[Total Target]  for all cluster) partners/stakeholders and reached [Total_Achieved], achieving [Total Target]/[Total_Achieved]% of the 	target.”). This information will be extracted from the IPI_1.1_Contributions.json. 
	From PDO5_Additional_question.json extract the responses for each cluster. Focus on the narratives answering these four questions and create a narrative for each cluster that contains:
1. Reference the knowledge products listed in the main narrative that are expected to be gender-sensitive and explain  how gender considerations are dealt with (e.g. 1- Gender-responsive infographic on pesticide use- examples tailored to women crop and schedule; 2-....)
2. Reference the knowledge products listed in the main narrative that are expected to address other social inclusion dimensions, and explain how those issues are dealt with. (e.g. 1 - Socially-equitable agro-advisory app- visualization  options for those with impaired vision: 2- ....)
3. Reference  the knowledge products listed in the main narrative that are expected to be led by a regional partner PPAs (AGRHYMET, ASARECA, CCARDESA, CORAF, ICPAC, and RUFORUM)
4. Reference  the knowledge products listed in the main narrative that are expected to be "just-in-time" or driven by parter requests. Explain how the knowledge products are expected to contribute to a change (e.g. policy, straregy, plans, capacity, innovation use, investments).
Note: Number and name the knowledge products/ decision making tools and advisory services expected to be reported this year end (e.g. 1- Policy brief on CoP for pastoralist; 2- Infonote on pesticide use; 3-..)



## Cluster-Level Achievements:
Do not group clusters together. Each cluster must be presented in its own section/paragraph. Create separate sections for each of the following clusters:



Senegal (Ensure to put the VALUE of End_year_achieved (from IPI_1.1_Contributions.json in the narrative)
Ghana (Ensure to put the VALUE of End_year_achieved (from IPI_1.1_Contributions.json in the narrative)
Zambia (Ensure to put the VALUE of End_year_achieved (from IPI_1.1_Contributions.json in the narrative)
Mali (Ensure to put the VALUE of End_year_achieved (from IPI_1.1_Contributions.json in the narrative)
Kenya (Ensure to put the VALUE of End_year_achieved (from IPI_1.1_Contributions.json in the narrative)
Ethiopia (Ensure to put the VALUE of End_year_achieved (from IPI_1.1_Contributions.json in the narrative)
EA (Ensure to put the VALUE of End_year_achieved (from IPI_1.1_Contributions.json in the narrative)
WA (Ensure to put the VALUE of End_year_achieved (from IPI_1.1_Contributions.json in the narrative)
Theme 1 (Ensure to put the VALUE of End_year_achieved (from IPI_1.1_Contributions.json in the narrative)
Theme 2 (Ensure to put the VALUE of End_year_achieved (from IPI_1.1_Contributions.json in the narrative)
Theme 3 (Ensure to put the VALUE of End_year_achieved (from IPI_1.1_Contributions.json in the narrative)
Theme 4 (Ensure to put the VALUE of End_year_achieved (from IPI_1.1_Contributions.json in the narrative)


For each cluster Ensure to put the VALUE of End_year_achieved in the narrative (don't summarise the thematics clusters), use the corresponding [Achieved_narrative] from IPI_1.1_Contributions.json and put the [End_year_achieved] (Ensure put the number for each cluster, Senegal, Ghana, Zambia, Mali, Kenya, Ethiopia, EA, WA, Theme 1, Theme 2, Theme 3, Theme 4)
Extract by cluster the insights from the IPI_1.1_Additional_question.json filtering by Cluster que column :
1. Reference the knowledge products listed in the main narrative that are expected to be gender-sensitive and explain  how gender considerations are dealt with (e.g. 1- Gender-responsive infographic on pesticide use- examples tailored to women crop and schedule; 2-....)
2. Reference the knowledge products listed in the main narrative that are expected to address other social inclusion dimensions, and explain how those issues are dealt with. (e.g. 1 - Socially-equitable agro-advisory app- visualization  options for those with impaired vision: 2- ....)
3. Reference  the knowledge products listed in the main narrative that are expected to be led by a regional partner PPAs (AGRHYMET, ASARECA, CCARDESA, CORAF, ICPAC, and RUFORUM)
4. Reference  the knowledge products listed in the main narrative that are expected to be "just-in-time" or driven by parter requests. Explain how the knowledge products are expected to contribute to a change (e.g. policy, straregy, plans, capacity, innovation use, investments).
Note: Number and name the knowledge products/ decision making tools and advisory services expected to be reported this year end (e.g. 1- Policy brief on CoP for pastoralist; 2- Infonote on pesticide use; 3-..)



--- 
# Conclusion:
Generate a narrative how the overall achievements and the separate, detailed cluster-level demonstrate Beneficiaries in the project area are increasingly accessing enhanced climate information services and/or validated climate-smart agriculture technologies.

# Important:
- Don't summarise of all, give me the all relevant details of each cluster in the IPI 1.1
- Do not combine or group clusters into one summary. Each cluster (8) must have its own clearly delineated section.
- The final output should be a single cohesive text in plain language, written in a formal and professional tone suitable for submission to the World Bank.
- Don't reference to the sources in the output.
- Ensure you put the following sections:
    - Introduction/Overview:
    - Overall Numerical Summary:
    - Cluster-Level Achievements
"""