def merge_knn_and_doi(knn_chunks: list[dict], doi_chunks: list[dict]) -> list[dict]:
    seen_keys = set()
    combined_chunks = []

    for chunk in knn_chunks + doi_chunks:
        doi = chunk.get("doi")
        cluster = chunk.get("cluster_acronym")
        indicator_code = chunk.get("indicator_acronym")

        if doi:
            key = (doi, cluster, indicator_code)
            if key not in seen_keys:
                seen_keys.add(key)
                combined_chunks.append(chunk)
        else:
            combined_chunks.append(chunk)

    return combined_chunks
