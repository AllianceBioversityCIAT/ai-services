POLICY_CHANGE_SECTION = """
⸻

Additional Requirements for "Policy Change"

Indicator definition:
• Refers to the introduction or modification of policies, strategies, or regulations addressing specific issues.
• Must show measurable impacts or outcomes aligned with the project/organization's goals.
• In PRMS this is an Outcome — it captures change in the policy environment attributable to research influence, not merely research recommendations or internal CGIAR policy.

What counts as a reportable policy change (use sources to judge candidacy):
• New or significantly updated policies, strategies, legal instruments, programs, budgets, or investments informed by CGIAR / Alliance research.
• Examples: national cultivar-release standards, biofortification guidelines embedded in release policy, budget lines or investment programs shaped by research evidence.

What typically does NOT qualify (do not classify as Policy Change):
• Policy recommendations or position papers produced by CGIAR alone, without evidence of uptake or enactment.
• Policy changes internal to CGIAR centers.
• Very localized policy changes with negligible scope (unless sources clearly treat them as significant outcomes).

Title and description context:
• A strong policy-change title is stand-alone: what changed, who implemented it, and where — include budget/investment in USD when explicitly stated.
• Description should explain the policy or legal instrument influenced, in plain language for non-specialists, including background not already in the title.

Policy type guidance:
• Policy or strategy — written decisions on, or commitments to, a particular course of action by an institution (policy); or a high-level plan outlining how that course of action will be carried out (strategy). Examples: country growth strategies, country agricultural policies, organization strategic plans or road maps, information campaigns for improved diets. These set goalposts but require other instruments for implementation.
• Legal instrument — laws (bills passed into law by parliament/congress or equivalent) or regulations (rules or norms adopted by a government) that dictate specific required or prohibited actions, often with implications for non-compliance.
• Program, budget or investment — implementing mechanisms that often follow from a strategy, policy or law, with defined actions over a period and often a budgetary amount. Examples: National Agricultural Investment Plans, ministry budgets, private-sector investments, programs launched by public, private and NGO sectors.


Type-specific block: policy_change (object, required for this indicator when type-specific data exists)

policy_type (object inside policy_change)
    • Return id and name together; must be one of:
        • id 1, name "Program, budget or investment"
        • id 2, name "Legal instrument"
        • id 3, name "Policy or strategy"
    • When id = 1, include status_amount (id + name) and amount (integer) if the sources state a budget or investment figure.
        • status_amount options: 
            • id 1, name "Confirmed" 
            • id 2, name "Estimated" 
            • id 3, name "Unknown"
        • amount is the budget or investment figure in USD if stated in sources.
    • When id = 2 or id = 3, do NOT include status_amount or amount.
    • Omit policy_type if the type cannot be determined from sources.

policy_stage (object inside policy_change)
    • Refers to the stage of the policy change process.
    • Return id and name together. The name must be exactly "Stage 1", "Stage 2", or "Stage 3" — do not include the definition in the name field.
    • Use the definitions below to choose the correct stage from the sources:
        • id 6, name "Stage 1" — Research taken up by next user, policy change not yet enacted.
        • id 7, name "Stage 2" — Policy enacted (provide link to published documents).
        • id 8, name "Stage 3" — Evidence of impact of policy (provide Key Result Story or evidence link).
    • Omit policy_stage if the stage cannot be determined from sources.

implementing_organization (array inside policy_change)
    • Organizations that implemented or formally adopted the policy change (government ministry, regulator, parliament, etc.).
    • These are external organizations — do NOT use the CGIAR centers reference list.
    • Return the organization name or acronym as extracted from sources.
    • Each item must contain exactly one of: institutions_name or institutions_acronym.
    • Example: [{"institutions_name": "Ministry of Agriculture Kenya"}, {"institutions_acronym": "MoA-Uganda"}]
    • Omit the array if not supported by sources.

Example:
{
    "policy_change": {
        "policy_type": {
            "id": 1,
            "name": "Program, budget or investment",
            "status_amount": {"id": 1, "name": "Confirmed"},
            "amount": 5000000
        },
        "policy_stage": {
            "id": 7,
            "name": "Stage 2"
        },
        "implementing_organization": [
            {"institutions_name": "Ministry of Agriculture Kenya"}
        ]
    }
}
"""
