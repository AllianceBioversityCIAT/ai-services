import requests

def map_fields_with_opensearch(mining_result, mapping_service_url):
    entries = []

    if contact := mining_result.get("main_contact_person", {}).get("name"):
        entries.append({"value": contact, "type": "staff"})

    if supervisor := mining_result.get("training_supervisor", {}).get("name"):
        entries.append({"value": supervisor, "type": "staff"})

    if affiliation := mining_result.get("trainee_affiliation", {}).get("affiliation_name"):
        entries.append({"value": affiliation, "type": "institution"})

    for partner in mining_result.get("partners", []):
        if partner_name := partner.get("name"):
            entries.append({"value": partner_name, "type": "institution"})

    if not entries:
        return mining_result

    try:
        response = requests.post(
            f"{mapping_service_url}/map/fields",
            json={"entries": entries},
            timeout=300
        )
        response.raise_for_status()
        mapped = response.json().get("results", [])

        # Asociar los IDs y scores de vuelta al resultado original
        for m in mapped:
            key = m["original_value"]
            if m["type"] == "staff":
                if key == mining_result.get("main_contact_person", {}).get("name"):
                    mining_result["main_contact_person"]["code"] = m["mapped_id"]
                    mining_result["main_contact_person"]["similarity_score"] = m["score"]
                elif key == mining_result.get("training_supervisor", {}).get("name"):
                    mining_result["training_supervisor"]["code"] = m["mapped_id"]
                    mining_result["training_supervisor"]["similarity_score"] = m["score"]

            elif m["type"] == "institution":
                if key == mining_result.get("trainee_affiliation", {}).get("affiliation_name"):
                    mining_result["trainee_affiliation"]["institution_id"] = m["mapped_id"]
                    mining_result["trainee_affiliation"]["similarity_score"] = m["score"]
                for p in mining_result.get("partners", []):
                    if p.get("name") == key:
                        p["institution_id"] = m["mapped_id"]
                        p["similarity_score"] = m["score"]
                        break

    except Exception as e:
        print(f"❌ Error mapping fields: {e}")

    return mining_result