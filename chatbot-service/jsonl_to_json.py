import json

input_path = "vw_ai_deliverables.jsonl"
output_path = "vw_ai_deliverables_openai.json"

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
                f"Deliverable ID: {data.get('ID', '')}\n"
                f"Indicator Acronym: {data.get('indicator_acronym', '')}\n"
                f"Cluster Acronym: {data.get('cluster_acronym', '')}\n"
                f"Title: {data.get('title', '')}\n"
                f"Description: {data.get('description', '')}\n"
                f"Year: {data.get('year', '')}\n"
                f"Category: {data.get('category', '')}\n"
                f"Sub Category: {data.get('sub_category', '')}\n"
                f"Status: {data.get('status', '')}\n"
                f"Gender Level: {data.get('gender_level', '')}\n"
                f"Youth Level: {data.get('youth_level', '')}\n"
                f"ISI Publication: {data.get('isi_publication', '')}\n"
                f"DLV is Open Access: {data.get('DLV_isOpenAcces', '')}\n"
                f"Activity Title: {data.get('activity_title', '')}\n"
                f"Activity Leader: {data.get('activity_leader', '')}\n"
                f"Link: {data.get('Link', '')}\n"
                f"Altmetric Score: {data.get('altmetric_score', '')}\n"
                f"Almetric Details: {data.get('almetric_details', '')}\n"
                f"Already Disseminated: {data.get('already_disseminated', '')}\n"
                f"Dissemination Channel: {data.get('dissemination_channel', '')}\n"
                f"Dissemination URL: {data.get('dissemination_URL', '')}\n"
                f"Is Melia Study: {data.get('is_melia_study', '')}\n"
                f"Study Type Name: {data.get('study_type_name', '')}\n"
                f"Study Type Description: {data.get('study_type_description', '')}\n"
                f"Updated Date: {data.get('updated_date', '')}\n"
                f"Partner Person: {data.get('partner_person', '')}\n"
                f"Partner Role: {data.get('partner_role', '')}\n"
                f"PPA Partner Name: {data.get('PPA_partner_name', '')}\n"
                f"PPA Partner Acronym: {data.get('ppa_partner_acronym', '')}\n"
                f"Geographic Scope: {data.get('geographic_scope', '')}\n"
                f"Cluster Role: {data.get('cluster_role', '')}\n"
                f"Cluster Owner Acronym: {data.get('cluster_owner_acronym', '')}\n"
                f"Is FAIR: {data.get('is_fair', '')}\n"
                f"Is Findable: {data.get('is_findable', '')}\n"
                f"Is Accessible: {data.get('is_Accessible', '')}\n"
                f"Is Interoperable: {data.get('is_Interoperable', '')}\n"
                f"Is Reusable: {data.get('is_Reusable', '')}\n"
                f"DOI: {data.get('doi', '')}\n"
                f"Shared Clusters Acronym: {data.get('shared_clusters_acronym', '')}\n"
                f"SHFRM Contribution Narrative: {data.get('shfrm_contribution_narrative', '')}\n"
                f"SHFRM Contribution Narrative AR: {data.get('shfrm_contribution_narrative_ar', '')}\n"
                f"SHFRM Action Name: {data.get('shfrm_action_name', '')}\n"
                f"SHFRM Action Desc: {data.get('shfrm_action_desc', '')}\n"
                f"SHFRM Sub Action Name: {data.get('shfrm_sub_action_name', '')}\n"
                f"SHFRM Sub Action Desc: {data.get('shfrm_sub_action_desc', '')}\n"
                f"Is Contributing SHFRM: {data.get('is_contributing_shfrm', '')}\n"
                f"Cluster Name: {data.get('cluster_name', '')}\n"
                f"Indicator Title: {data.get('indicator_title', '')}\n"
                f"Institution Acronym: {data.get('institution_acronym', '')}\n"
                f"Name: {data.get('name', '')}\n"
                f"Institution Type: {data.get('institution_type', '')}\n"
                f"Country Name: {data.get('country_name', '')}\n"
                f"Region Name: {data.get('region_name', '')}\n"
                f"Table Type: {data.get('table_type', '')}\n"
            )
        }
        docs.append(doc)

with open(output_path, "w", encoding="utf-8") as outfile:
    json.dump(docs, outfile, ensure_ascii=False, indent=2)

print(f"Archivo convertido y guardado en {output_path}")