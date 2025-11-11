import uuid
import os
import json
from typing import List, Dict, Optional
from app.models import GeneratedQuestion, MCQOption

# Try to import OpenAI
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("OpenAI not installed. Run: pip install openai")


# ============================================================================
# AI-Powered Question Generation (Production)
# ============================================================================

async def generate_questions_from_text(
    text: str,
    num_questions: int = 10,
    mix: Optional[Dict[str, int]] = None
) -> List[GeneratedQuestion]:
    """
    Generate questions from text using OpenAI GPT-4.
    Falls back to template-based generation if API key not available.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    
    if api_key and OPENAI_AVAILABLE:
        print("Using OpenAI GPT-4 for question generation...")
        try:
            return await generate_questions_with_openai(text, num_questions, mix, api_key)
        except Exception as e:
            print(f"OpenAI generation failed: {e}")
            print("Falling back to template-based generation...")
            return await generate_questions_template_based(text, num_questions, mix)
    else:
        if not api_key:
            print("No OPENAI_API_KEY found, using template-based generation")
        if not OPENAI_AVAILABLE:
            print("OpenAI library not installed, using template-based generation")
        return await generate_questions_template_based(text, num_questions, mix)


async def generate_questions_with_openai(
    text: str,
    num_questions: int = 10,
    mix: Optional[Dict[str, int]] = None,
    api_key: Optional[str] = None
) -> List[GeneratedQuestion]:
    """
    Generate high-quality questions using OpenAI GPT-4.
    """
    if mix is None:
        mix = {
            "mcq": int(num_questions * 0.6),
            "fill_blank": int(num_questions * 0.2),
            "short_answer": int(num_questions * 0.2),
        }
    
    client = AsyncOpenAI(api_key=api_key)
    
    # Create the prompt
    prompt = f"""You are an expert educator creating exam questions from lecture content.

Lecture Content:
{text[:3000]}  # Limit to avoid token limits

Generate {num_questions} questions with this distribution:
- {mix['mcq']} Multiple Choice Questions (MCQ) with 4 options each
- {mix['fill_blank']} Fill-in-the-blank questions
- {mix['short_answer']} Short answer questions

Distribute difficulty as: 1/3 easy, 1/3 medium, 1/3 hard

For each question, provide:
1. Question type (mcq, fill_blank, or short_answer)
2. The question text/prompt
3. Correct answer
4. For MCQ: 4 options (mark which is correct)
5. Brief explanation of the answer
6. Main topic/concept being tested
7. Difficulty level (easy, medium, or hard)

Return ONLY a valid JSON array with this exact structure:
[
  {{
    "type": "mcq",
    "prompt": "Question text here?",
    "options": [
      {{"text": "Option A text", "is_correct": true}},
      {{"text": "Option B text", "is_correct": false}},
      {{"text": "Option C text", "is_correct": false}},
      {{"text": "Option D text", "is_correct": false}}
    ],
    "answer": "Option A text",
    "explanation": "Brief explanation here",
    "topic": "Main concept",
    "difficulty": "medium"
  }},
  {{
    "type": "fill_blank",
    "prompt": "The _____ is a key concept in this lecture.",
    "options": null,
    "answer": "specific term",
    "explanation": "Brief explanation",
    "topic": "Main concept",
    "difficulty": "easy"
  }},
  {{
    "type": "short_answer",
    "prompt": "Explain the significance of...",
    "options": null,
    "answer": "Expected answer keywords",
    "explanation": "What to look for in answer",
    "topic": "Main concept",
    "difficulty": "hard"
  }}
]

CRITICAL: Return ONLY the JSON array, no other text."""

    try:
        # Call OpenAI API
        response = await client.chat.completions.create(
            model="gpt-4-turbo-preview",  # or "gpt-4" or "gpt-3.5-turbo"
            messages=[
                {"role": "system", "content": "You are an expert educator who creates high-quality exam questions. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3000,
        )
        
        # Parse response
        content = response.choices[0].message.content.strip()
        
        # Clean up response (remove markdown if present)
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Parse JSON
        questions_data = json.loads(content)
        
        # Convert to GeneratedQuestion objects
        questions = []
        for q_data in questions_data:
            # Convert options if present
            options = None
            if q_data.get("options"):
                options = [
                    MCQOption(text=opt["text"], is_correct=opt.get("is_correct", False))
                    for opt in q_data["options"]
                ]
            
            question = GeneratedQuestion(
                type=q_data["type"],
                prompt=q_data["prompt"],
                options=options,
                answer=q_data["answer"],
                explanation=q_data.get("explanation"),
                topic=q_data.get("topic"),
                difficulty=q_data.get("difficulty", "medium"),
            )
            questions.append(question)
        
        print(f"✓ Generated {len(questions)} AI-powered questions")
        return questions
        
    except json.JSONDecodeError as e:
        print(f"Failed to parse OpenAI response as JSON: {e}")
        print(f"Response was: {content[:500]}")
        raise Exception("OpenAI returned invalid JSON")
    except Exception as e:
        print(f"OpenAI API error: {e}")
        raise


# ============================================================================
# Template-Based Generation (Fallback)
# ============================================================================

async def generate_questions_template_based(
    text: str,
    num_questions: int = 10,
    mix: Optional[Dict[str, int]] = None
) -> List[GeneratedQuestion]:
    """
    Generate questions using templates (fallback when AI not available).
    """
    if mix is None:
        mix = {
            "mcq": int(num_questions * 0.6),
            "fill_blank": int(num_questions * 0.2),
            "short_answer": int(num_questions * 0.2),
        }
    
    questions = []
    concepts = extract_concepts(text, num_questions * 2)
    difficulties = ["easy", "medium", "hard"]
    
    # Generate MCQ questions
    for i in range(mix.get("mcq", 0)):
        concept = concepts[i % len(concepts)]
        difficulty = difficulties[i % 3]
        question = generate_mcq_question(concept, difficulty)
        questions.append(question)
    
    # Generate fill-in-the-blank
    for i in range(mix.get("fill_blank", 0)):
        concept = concepts[(i + mix["mcq"]) % len(concepts)]
        difficulty = difficulties[i % 3]
        question = generate_fill_blank_question(concept, difficulty)
        questions.append(question)
    
    # Generate short answer
    for i in range(mix.get("short_answer", 0)):
        concept = concepts[(i + mix["mcq"] + mix["fill_blank"]) % len(concepts)]
        difficulty = difficulties[i % 3]
        question = generate_short_answer_question(concept, difficulty)
        questions.append(question)
    
    print(f"✓ Generated {len(questions)} template-based questions")
    return questions


async def summarize_text(text: str) -> str:
    """Generate a summary of the text."""
    if not text:
        return "No content provided"
    
    words = text.split()
    if len(words) > 50:
        summary = ' '.join(words[:50]) + "..."
    else:
        summary = text
    return summary


# ============================================================================
# Helper Functions (for template-based generation)
# ============================================================================

def extract_concepts(text: str, num_concepts: int = 5) -> List[str]:
    """Extract key concepts from text."""
    words = text.lower().split()
    common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "is", "was", "are", "of", "it", "that", "this"}
    concepts = [w for w in words if len(w) > 5 and w not in common_words]
    
    unique_concepts = list(set(concepts))[:num_concepts]
    
    if not unique_concepts:
        unique_concepts = ["concept", "principle", "topic"]
    
    return unique_concepts


def generate_mcq_question(concept: str, difficulty: str) -> GeneratedQuestion:
    """Generate an MCQ question."""
    prompts = {
        "easy": f"What is the primary purpose of {concept}?",
        "medium": f"How does {concept} function in practical applications?",
        "hard": f"Analyze the implications of {concept} in complex scenarios.",
    }
    
    correct_opt = MCQOption(
        text=f"{concept.capitalize()} enables efficient processing and optimization",
        is_correct=True
    )
    
    incorrect_opts = [
        MCQOption(text=f"{concept.capitalize()} is primarily decorative", is_correct=False),
        MCQOption(text=f"{concept.capitalize()} has no practical applications", is_correct=False),
        MCQOption(text=f"{concept.capitalize()} is an outdated approach", is_correct=False),
    ]
    
    options = [correct_opt] + incorrect_opts
    
    return GeneratedQuestion(
        type="mcq",
        prompt=prompts.get(difficulty, prompts["medium"]),
        options=options,
        answer=correct_opt.text,
        explanation=f"The correct answer explains how {concept} functions in the context discussed.",
        topic=concept,
        difficulty=difficulty,
    )


def generate_fill_blank_question(concept: str, difficulty: str) -> GeneratedQuestion:
    """Generate a fill-in-the-blank question."""
    prompts = {
        "easy": f"The _____ is essential for understanding this topic.",
        "medium": f"In modern applications, _____ plays a critical role.",
        "hard": f"Advanced implementations leverage _____ to achieve optimal results.",
    }
    
    return GeneratedQuestion(
        type="fill_blank",
        prompt=prompts.get(difficulty, prompts["medium"]),
        options=None,
        answer=concept,
        explanation=f"The blank should be filled with '{concept}' based on the lecture context.",
        topic=concept,
        difficulty=difficulty,
    )


def generate_short_answer_question(concept: str, difficulty: str) -> GeneratedQuestion:
    """Generate a short answer question."""
    prompts = {
        "easy": f"Briefly describe {concept}.",
        "medium": f"Explain how {concept} is applied in real-world scenarios.",
        "hard": f"Critically evaluate the role of {concept} in solving complex problems.",
    }
    
    answers = {
        "easy": f"A concise explanation of {concept}",
        "medium": f"Practical applications of {concept}",
        "hard": f"Critical analysis of {concept}",
    }
    
    return GeneratedQuestion(
        type="short_answer",
        prompt=prompts.get(difficulty, prompts["medium"]),
        options=None,
        answer=answers.get(difficulty, answers["medium"]),
        explanation=f"A strong answer should demonstrate understanding of {concept} as discussed in the lecture.",
        topic=concept,
        difficulty=difficulty,
    )