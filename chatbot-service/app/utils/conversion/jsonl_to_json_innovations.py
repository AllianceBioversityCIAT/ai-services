import json

input_path = "vw_ai_innovations.jsonl"
output_path = "vw_ai_innovations_openai.json"

docs = []
with open(input_path, "r", encoding="utf-8") as infile:
    for line in infile:
        data = json.loads(line)
        doc = {
            "indicator_acronym": data.get("indicator_acronym", ""),
            "year": data.get("year", ""),
            "table_type": data.get("table_type", ""),
            "phase_name": data.get("phase_name", ""),
            "cluster_acronym": data.get("cluster_acronym", ""),
            "content": (
                f"ID: {data.get('id', '')}\n"
                f"Indicator Acronym: {data.get('indicator_acronym', '')}\n"
                f"Cluster Acronym: {data.get('cluster_acronym', '')}\n"
                f"Link Innovation: {data.get('link_innovation', '')}\n"
                f"Link PDF Innovation: {data.get('link_pdf_innovation', '')}\n"
                f"Year: {data.get('year', '')}\n"
                f"Title: {data.get('title', '')}\n"
                f"Narrative: {data.get('narrative', '')}\n"
                f"Type: {data.get('type', '')}\n"
                f"Geographic Scope: {data.get('geographic_scope', '')}\n"
                f"Region: {data.get('region', '')}\n"
                f"Country: {data.get('country', '')}\n"
                f"Cluster Role: {data.get('cluster_role', '')}\n"
                f"Cluster Owner Acronym: {data.get('cluster_owner_acronym', '')}\n"
                f"Updated Date: {data.get('updated_date', '')}\n"
                f"Shared Clusters Acronym: {data.get('shared_clusters_acronym', '')}\n"
                f"Institution Name: {data.get('institution_name', '')}\n"
                f"Partner Role: {data.get('partner_role', '')}\n"
                f"Org Type: {data.get('org_type', '')}\n"
                f"Institution Type: {data.get('institution_type', '')}\n"
                f"Actor Name: {data.get('actor_name', '')}\n"
                f"Actor Name CGIAR: {data.get('actor_name_cgiar', '')}\n"
                f"Other: {data.get('other', '')}\n"
                f"Total: {data.get('total', '')}\n"
                f"Is Women Youth: {data.get('is_women_youth', '')}\n"
                f"Is Women Not Youth: {data.get('is_women_not_youth', '')}\n"
                f"Is Men Youth: {data.get('is_men_youth', '')}\n"
                f"Is Men Not Youth: {data.get('is_men_not_youth', '')}\n"
                f"Is Nonbinary Youth: {data.get('is_nonbinary_youth', '')}\n"
                f"Is Nonbinary Not Youth: {data.get('is_nonbinary_not_youth', '')}\n"
                f"Is Sex Age Not Apply: {data.get('is_sex_age_not_apply', '')}\n"
                f"Readiness Scale: {data.get('readiness_scale', '')}\n"
                f"Readiness Reason: {data.get('readiness_reason', '')}\n"
                f"Innovation Nature: {data.get('innovation_nature', '')}\n"
                f"Innovation Nature Definition: {data.get('innovation_nature_definition', '')}\n"
                f"Readiness Name: {data.get('readiness_name', '')}\n"
                f"Readiness Name Description: {data.get('readiness_name_description', '')}\n"
                f"Beneficiaries Narrative: {data.get('beneficiaries_narrative', '')}\n"
                f"Innovation Importance: {data.get('innovation_importance', '')}\n"
                f"Knowledge Tool Uses Narrative: {data.get('knowledge_tool_uses_narrative', '')}\n"
                f"Knowledge Results Narrative: {data.get('knowledge_results_narrative', '')}\n"
                f"Knowledge Collaboration: {data.get('knowledge_collaboration', '')}\n"
                f"Knowledge Methods and Tools Narrative: {data.get('knowledge_methods_and_tools_narrative', '')}\n"
                f"Reason Knowledge Potential: {data.get('reason_knowledge_potential', '')}\n"
                f"Is Innovation Bundle: {data.get('is_innovation_bundle', '')}\n"
                f"Complementary Solution Title: {data.get('complementary_solution_title', '')}\n"
                f"Complementary Solution Type Name: {data.get('complementary_solution_type_name', '')}\n"
                f"Function Title: {data.get('function_title', '')}\n"
                f"Selected Innovation ID: {data.get('selected_innovation_id', '')}\n"
                f"Selected Title: {data.get('selected_title', '')}\n"
                f"Selected Link: {data.get('selected_link', '')}\n"
                f"Indicator Title: {data.get('indicator_title', '')}\n"
                f"Country Name: {data.get('country_name', '')}\n"
                f"Table Type: {data.get('table_type', '')}\n"
            )
        }
        docs.append(doc)

with open(output_path, "w", encoding="utf-8") as outfile:
    json.dump(docs, outfile, ensure_ascii=False, indent=2)

print(f"Archivo convertido y guardado en {output_path}")