"""Mock database of vetted charitable organizations."""


def get_charities_by_cause(cause_area: str):
    """Returns list of charities for a given cause area."""

    charities_db = {
        "education": [
            {
                "name": "Room to Read",
                "ein": "77-0479905",
                "mission": "Transforms the lives of millions of children in low-income communities by focusing on literacy and gender equality in education.",
                "rating": 4.9,
                "efficiency": 0.88,  # 88% of funds go to programs
                "cause": "education"
            },
            {
                "name": "Teach For America",
                "ein": "13-3541913",
                "mission": "Works to expand educational opportunity for children facing adversity.",
                "rating": 4.7,
                "efficiency": 0.81,
                "cause": "education"
            },
            {
                "name": "Tech Education Alliance",
                "ein": "45-2345678",
                "mission": "Brings computer science education to underserved schools.",
                "rating": 4.8,
                "efficiency": 0.92,
                "cause": "education"
            }
        ],
        "health": [
            {
                "name": "Doctors Without Borders",
                "ein": "13-3433452",
                "mission": "Provides emergency medical aid to people affected by conflict, epidemics, disasters, or exclusion from healthcare.",
                "rating": 5.0,
                "efficiency": 0.89,
                "cause": "health"
            }
        ],
        "environment": [
            {
                "name": "The Nature Conservancy",
                "ein": "53-0242652",
                "mission": "Conserves the lands and waters on which all life depends.",
                "rating": 4.6,
                "efficiency": 0.77,
                "cause": "environment"
            }
        ]
    }

    return charities_db.get(cause_area.lower(), [])
