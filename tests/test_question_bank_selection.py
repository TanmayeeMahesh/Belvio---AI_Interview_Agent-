import extraction


def test_select_questions_from_question_bank_uses_experience_and_gaps():
    analysis = {
        "jobRole": "Software Engineer",
        "detectedLevel": "intermediate",
        "yearsExperience": 2,
        "skills": ["Python", "Git"],
        "missingSkills": ["Docker", "System Design"],
        "analysisSummary": "Strong Python developer with some team experience.",
    }

    questions = extraction.select_questions_from_question_bank(
        analysis,
        role="Software Engineer",
        question_count=5,
    )

    assert len(questions) == 5
    assert {q["topic"] for q in questions} == {
        "Core Concepts",
        "Role-Specific Fundamentals",
        "Tools & Technologies",
        "Frameworks & Methodologies",
        "Industry Knowledge",
    }
    assert sum(1 for q in questions if q.get("selection_reason") == "gap") == 2
    assert sum(1 for q in questions if q.get("source") == "gap_analysis") == 2
    assert sum(1 for q in questions if q.get("selection_reason") == "common") == 4
    assert sum(1 for q in questions if q.get("source") == "question_bank") == 9
