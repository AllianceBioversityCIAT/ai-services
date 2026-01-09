import json

input_path = "vw_ai_oicrs.jsonl"
output_path = "vw_ai_oicrs_openai.json"

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
                f"OICR ID: {data.get('oicr_id', '')}\n"
                f"Indicator Acronym: {data.get('indicator_acronym', '')}\n"
                f"Cluster Acronym: {data.get('cluster_acronym', '')}\n"
                f"Cluster Owner Acronym: {data.get('cluster_owner_acronym', '')}\n"
                f"Cluster Role: {data.get('cluster_role', '')}\n"
                f"Link OICR ID: {data.get('link_oicr_id', '')}\n"
                f"Link PDF OICR: {data.get('link_pdf_oicr', '')}\n"
                f"Study Type: {data.get('study_type', '')}\n"
                f"Status: {data.get('status', '')}\n"
                f"Year: {data.get('year', '')}\n"
                f"Title: {data.get('Title', '')}\n"
                f"Short Impact Statement: {data.get('short_impact_statement', '')}\n"
                f"Maturity Level: {data.get('maturity_level', '')}\n"
                f"SRF Target: {data.get('srf_target', '')}\n"
                f"Top Level Comment: {data.get('top_level_comment', '')}\n"
                f"Geographic Scope: {data.get('geographic_scope', '')}\n"
                f"Region: {data.get('region', '')}\n"
                f"Country: {data.get('country', '')}\n"
                f"Scope Comment: {data.get('scope_comment', '')}\n"
                f"Contributing Regions: {data.get('contributing_regions', '')}\n"
                f"Partner Name: {data.get('partner_name', '')}\n"
                f"CGIAR Innovation: {data.get('cgiar_innovation', '')}\n"
                f"Innovation Title: {data.get('innovation_title', '')}\n"
                f"Elaboration Statement: {data.get('elaboration_statement', '')}\n"
                f"References Cited: {data.get('references_cited', '')}\n"
                f"Gender: {data.get('gender', '')}\n"
                f"Gender Relevance Description: {data.get('gender_relevance_despcription', '')}\n"
                f"Youth: {data.get('youth', '')}\n"
                f"Youth Relevance Description: {data.get('youth_relevance_despcription', '')}\n"
                f"Capdev: {data.get('capdev', '')}\n"
                f"Capdev Relevance Description: {data.get('capdev_relevance_despcription', '')}\n"
                f"Climate: {data.get('climate', '')}\n"
                f"Climate Relevance Description: {data.get('climate_relevance_despcription', '')}\n"
                f"Contact Person: {data.get('contact_person', '')}\n"
                f"Updated Date: {data.get('updated_date', '')}\n"
                f"Center Name: {data.get('center_name', '')}\n"
                f"Shared Clusters: {data.get('shared_clusters', '')}\n"
                f"Feedback Score: {data.get('feedback_score', '')}\n"
                f"Tag Name: {data.get('tag_name', '')}\n"
                f"Indicator Title: {data.get('indicator_title', '')}\n"
                f"Country Name: {data.get('country_name', '')}\n"
                f"Institution Name: {data.get('institution_name', '')}\n"
                f"Institution Short Name: {data.get('institution_short_name', '')}\n"
                f"Table Type: {data.get('table_type', '')}\n"
            )
        }
        docs.append(doc)

with open(output_path, "w", encoding="utf-8") as outfile:
    json.dump(docs, outfile, ensure_ascii=False, indent=2)

print(f"Archivo convertido y guardado en {output_path}")