"""Prompt template for generating Challenges and Lessons Learned reports."""

def generate_challenges_prompt(year):  
    return f"""
# Challenges and Lessons Learned Report - {year}

Generate a comprehensive report about the challenges faced and lessons learned by AICCRA clusters during {year}. This report should provide insights into implementation difficulties, adaptive strategies, and key learnings that can inform future activities.

## Report Structure:

### 1. Executive Summary
- Brief overview of major challenges and key lessons learned across all clusters
- Highlight 3-5 most significant insights that emerged during {year}

### 2. Challenges by Cluster
For each cluster that provided data, create a dedicated section with:
- **Cluster Name** (bold formatting)
- **Main Challenges**: List and describe the primary obstacles faced
- **Impact Assessment**: How these challenges affected project implementation
- **Mitigation Strategies**: Actions taken to address the challenges

### 3. Lessons Learned by Cluster  
For each cluster:
- **Cluster Name** (bold formatting)
- **Key Learnings**: Most important insights gained
- **Best Practices**: Successful strategies and approaches
- **Adaptive Measures**: How the cluster adapted to overcome difficulties

### 4. Cross-Cutting Themes
Identify common patterns across clusters:
- **Recurring Challenges**: Issues faced by multiple clusters
- **Shared Solutions**: Strategies that worked across different contexts
- **Systemic Insights**: Learnings about the broader AICCRA approach

### 5. Strategic Recommendations
Based on the challenges and lessons learned:
- **Short-term Actions**: Immediate steps to address current challenges
- **Medium-term Strategies**: Approaches for improving future implementation
- **Knowledge Sharing**: Recommendations for spreading successful practices

## Formatting Guidelines:
- Use clear headings and subheadings
- Bold cluster names for easy identification
- Use bullet points for listing challenges and lessons
- Include specific examples and details from the context
- Maintain a constructive tone focused on learning and improvement
- Ensure each cluster's unique context and contributions are reflected

## Content Requirements:
- Draw exclusively from the provided context data
- Ensure all clusters mentioned in the data are covered
- Maintain factual accuracy and avoid speculation
- Highlight both challenges and positive learnings
- Focus on actionable insights and practical recommendations

Generate a comprehensive, well-structured report that captures the full spectrum of challenges and lessons learned across AICCRA's implementation in {year}.
"""