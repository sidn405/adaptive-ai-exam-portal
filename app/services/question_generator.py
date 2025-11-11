import os
from typing import List, Dict, Any

from fastapi import HTTPException
from app.models import GeneratedQuestion, MCQOption

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


async def summarize_text(text: str) -> str:
    # simple stub – swap with real summarizer later
    return text[:1500]


async def generate_questions_from_text(
    text: str,
    num_questions: int = 10,
    mix: Dict[str, int] | None = None,
) -> List[GeneratedQuestion]:
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY not set for question generation.",
        )

    mix = mix or {
        "mcq": int(num_questions * 0.6),
        "fill_blank": int(num_questions * 0.2),
        "short_answer": num_questions
        - int(num_questions * 0.6)
        - int(num_questions * 0.2),
    }

    import openai  # type: ignore

    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    system_prompt = (
        "You generate exam questions from lecture text. "
        "Return STRICT JSON with a list of questions. "
        "Each question MUST have: type (mcq|fill_blank|short_answer), "
        "prompt, options (for mcq), answer, explanation, topic, difficulty. "
        "For MCQ, options can be an array of strings OR objects with "
        "text and is_correct."
    )

    user_prompt = f"""
Lecture content:
{text[:8000]}

Generate exactly {num_questions} questions using this mix:
- MCQ: {mix['mcq']}
- Fill in the blank: {mix['fill_blank']}
- Short answer: {mix['short_answer']}

Respond in JSON:
{{
  "questions": [
    {{
      "type": "mcq",
      "prompt": "...",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "Correct option text",
      "explanation": "...",
      "topic": "...",
      "difficulty": "easy|medium|hard"
    }},
    ...
  ]
}}
"""

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )

    import json

    data = json.loads(resp.choices[0].message.content)
    questions_raw = data.get("questions", [])

    questions: List[GeneratedQuestion] = []

    for q in questions_raw:
        # --- normalize type ---
        raw_type = str(q.get("type", "mcq")).strip().lower()
        if raw_type in ("mcq", "multiple_choice", "multiple-choice", "multiple choice"):
            q_type = "mcq"
        elif raw_type in (
            "fill_blank",
            "fill-in-the-blank",
            "fill_in_the_blank",
            "fill in the blank",
            "fitb",
        ):
            q_type = "fill_blank"
        else:
            q_type = "short_answer"

        # --- normalize difficulty ---
        raw_diff = str(q.get("difficulty", "medium") or "medium").strip().lower()
        if raw_diff.startswith("e"):
            difficulty = "easy"
        elif raw_diff.startswith("h"):
            difficulty = "hard"
        else:
            difficulty = "medium"

        answer_text = q.get("answer") or ""

        # --- MCQ options parsing (robust) ---
        options = None
        if q_type == "mcq":
            options_list: Any = q.get("options") or []
            parsed_options: List[MCQOption] = []

            if isinstance(options_list, list) and options_list:
                for opt in options_list:
                    if isinstance(opt, dict):
                        text = opt.get("text") or opt.get("label") or str(opt)
                        is_corr = bool(opt.get("is_correct"))
                    else:
                        # opt is a string
                        text = str(opt)
                        is_corr = _norm(text) == _norm(answer_text)
                    parsed_options.append(MCQOption(text=text, is_correct=is_corr))
            else:
                # If no options given, fabricate basic ones from the answer
                if answer_text:
                    parsed_options = [
                        MCQOption(text=answer_text, is_correct=True),
                        MCQOption(text="None of the above", is_correct=False),
                    ]

            options = parsed_options or None

        questions.append(
            GeneratedQuestion(
                type=q_type,
                prompt=q.get("prompt", "") or "",
                options=options,
                answer=answer_text,
                explanation=q.get("explanation"),
                topic=q.get("topic"),
                difficulty=difficulty,
            )
        )

    return questions
