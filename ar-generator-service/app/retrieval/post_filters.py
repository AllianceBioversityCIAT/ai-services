def filter_midyear_chunks(chunks: list[dict]) -> list[dict]:
    return [
        chunk for chunk in chunks
        if not (
            (chunk.get("table_type") == "deliverables" and chunk.get("cluster_role") == "Shared")
            or (chunk.get("table_type") == "innovations" and chunk.get("cluster_role") == "Shared")
        )
    ]


def should_exclude_knn_chunk(chunk: dict) -> bool:
    return (
        (chunk.get("table_type") == "deliverables" and chunk.get("cluster_role") == "Shared")
        or (chunk.get("table_type") == "deliverables" and chunk.get("status") == "Cancelled")
        or (chunk.get("table_type") == "innovations" and chunk.get("cluster_role") == "Shared")
        or (chunk.get("table_type") == "oicrs" and chunk.get("cluster_role") == "Shared")
        or (chunk.get("table_type") == "contributions" and chunk.get("phase_name") == "AWPB")
        or (chunk.get("table_type") == "contributions" and chunk.get("phase_name") == "Progress")
    )


def filter_annual_knn_chunks(chunks: list[dict]) -> list[dict]:
    return [chunk for chunk in chunks if not should_exclude_knn_chunk(chunk)]


def filter_questions_chunks(chunks: list[dict]) -> list[dict]:
    return [
        chunk for chunk in chunks
        if not (
            (chunk.get("table_type") == "questions" and chunk.get("phase_name") == "AWPB")
            or (chunk.get("table_type") == "questions" and chunk.get("phase_name") == "Progress")
            or (chunk.get("table_type") == "contributions" and chunk.get("phase_name") == "AWPB")
            or (chunk.get("table_type") == "contributions" and chunk.get("phase_name") == "Progress")
            or (
                chunk.get("indicator_acronym") == "PDO Indicator 1"
                and chunk.get("question", "").startswith("2.0")
            )
            or (
                chunk.get("indicator_acronym") == "PDO Indicator 2"
                and chunk.get("question", "").startswith("3.0")
            )
            or (
                chunk.get("indicator_acronym") == "PDO Indicator 3"
                and chunk.get("question", "").startswith("3.0")
            )
            or (
                chunk.get("indicator_acronym") == "IPI 2.3"
                and chunk.get("question", "").startswith("0")
            )
            or (
                chunk.get("indicator_acronym") == "IPI 2.3"
                and chunk.get("question", "").startswith("1")
            )
            or (
                chunk.get("indicator_acronym") == "IPI 2.3"
                and chunk.get("question", "").startswith("2")
            )
        )
    ]
