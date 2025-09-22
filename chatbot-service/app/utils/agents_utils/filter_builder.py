def filter_metadata(phase, section, indicator):
    year = (
        next((p for p in phase.split() if p.isdigit()), None)
        if phase and phase != "All phases" and "None" not in phase
        else None
    )

    phase_name = (
        next((p for p in phase.split() if not p.isdigit()), None)
        if phase and phase != "All phases" and "None" not in phase
        else None
    )

    filter_conditions = []
    
    if section is not None and section != "All sections":
        if section.lower() == "contributions":
            filter_conditions.append({
                'orAll': [
                    {
                        'equals': {
                            "key": "table_type",
                            "value": "contributions"
                        }
                    },
                    {
                        'equals': {
                            "key": "table_type",
                            "value": "questions"
                        }
                    }
                ]
            })
        else:
            filter_conditions.append({
                'equals': {
                    "key": "table_type",
                    "value": section.lower()
                }
            })
    
    if indicator is not None and indicator != "All indicators":
        filter_conditions.append({
            'equals': {
                "key": "indicator_acronym",
                "value": indicator
            }
        })
    
    if year is not None:
        filter_conditions.append({
            'equals': {
                "key": "year",
                "value": year
            }
        })

    if phase_name is not None and section.lower() == "contributions":
        filter_conditions.append({
            'equals': {
                "key": "phase_name",
                "value": phase_name
            }
        })

    vector_search_config = {
        "numberOfResults": 30,
        "overrideSearchType": "HYBRID"
    }

    if filter_conditions:
        if len(filter_conditions) == 1:
            # If only one condition, use it directly instead of wrapping in andAll
            vector_search_config["filter"] = filter_conditions[0]
        else:
            # If multiple conditions, use andAll
            vector_search_config["filter"] = {"andAll": filter_conditions}
    
    return vector_search_config