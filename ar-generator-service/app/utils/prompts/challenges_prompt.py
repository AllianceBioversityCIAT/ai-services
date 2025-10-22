"""Prompt template for generating Challenges and Lessons Learned reports."""

def generate_challenges_prompt(year):  
    return f"""
# Challenges and Lessons Learned Report - {year}

Generate a comprehensive report about the challenges faced and lessons learned by AICCRA clusters during {year}. This report should provide insights into implementation difficulties, adaptive strategies, and key learnings that can inform future activities.

## Report Structure:

### Executive Summary
- Brief overview of major challenges and key lessons learned across all clusters during {year}

### 1. Challenges, Causes, and Proposed Solutions
For each cluster that provided data, create a dedicated section with:
- **Cluster Name** (bold formatting)
- **Main Challenges**: List and describe all the obstacles faced
- **Impact Assessment**: How these challenges affected project implementation (if provided)
- **Mitigation Strategies**: Actions taken to address the challenges (if provided)

### 2. Lessons Learned
For each cluster:
- **Cluster Name** (bold formatting)
- **Key Learnings**: All insights gained
- **Best Practices**: Successful strategies and approaches (if provided)
- **Adaptive Measures**: How the cluster adapted to overcome difficulties (if provided)

## Formatting Guidelines:
- Use clear headings and subheadings
- Bold cluster names for easy identification
- Use one or two paragraphs per cluster to mention challenges and lessons, depending on the amount of content available (challenges and lessons have to be in separate paragraphs)
- Include specific examples and details from the context
- Maintain a constructive tone focused on learning and improvement
- Ensure each cluster's unique context and contributions are reflected
- Do not include any information outside of the provided context

## Content Requirements:
- Draw exclusively from the provided context data
- Ensure all clusters that provided data about challenges and lessons learned are covered
- Maintain factual accuracy and avoid speculation
- Highlight both challenges and positive learnings
- Focus on actionable insights and practical recommendations

Generate a comprehensive, well-structured report that captures the full spectrum of challenges and lessons learned across AICCRA's implementation in {year}.
"""