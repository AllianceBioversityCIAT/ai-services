import json

input_path = "vw_ai_questions.jsonl"
output_path = "vw_ai_questions_openai.json"

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
                f"Year: {data.get('year', '')}\n"
                f"Phase Name: {data.get('phase_name', '')}\n"
                f"Project Link: {data.get('Project Link', '')}\n"
                f"Question: {data.get('question', '')}\n"
                f"Narrative: {data.get('narrative', '')}\n"
                f"Cluster Acronym: {data.get('cluster_acronym', '')}\n"
                f"Cluster Name: {data.get('cluster_name', '')}\n"
                f"Indicator Acronym: {data.get('indicator_acronym', '')}\n"
                f"Indicator Title: {data.get('indicator_title', '')}\n"
                f"Table Type: {data.get('table_type', '')}\n"
            )
        }
        docs.append(doc)

with open(output_path, "w", encoding="utf-8") as outfile:
    json.dump(docs, outfile, ensure_ascii=False, indent=2)

print(f"Archivo convertido y guardado en {output_path}")