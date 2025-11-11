import uuid
from typing import List, Dict, Optional
from app.models import GeneratedQuestion, MCQOption


# ============================================================================
# Helper Functions
# ============================================================================

def extract_concepts(text: str, num_concepts: int = 5) -> List[str]:
    """
    Extract key concepts from text.
    In production, use NLP libraries like spaCy or GPT-4.
    """
    # Simple keyword extraction (would use NLP in production)
    words = text.lower().split()
    # Filter common words and extract potential concepts
    common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
    concepts = [w for w in words if len(w) > 5 and w not in common_words]
    
    # Return unique concepts
    unique_concepts = list(set(concepts))[:num_concepts]
    
    # Fallback concepts if text is too short
    if not unique_concepts:
        unique_concepts = ["fundamental concept", "key principle", "important topic"]
    
    return unique_concepts


async def summarize_text(text: str) -> str:
    """
    Generate a summary of the text.
    In production, use GPT-4 or similar.
    """
    # Simple summarization (first 200 chars + concepts)
    concepts = extract_concepts(text, 3)
    summary = f"{text[:200]}... Key topics: {', '.join(concepts)}"
    return summary


async def generate_questions_from_text(
    text: str,
    num_questions: int = 10,
    mix: Optional[Dict[str, int]] = None
) -> List[GeneratedQuestion]:
    """
    Generate questions from text content.
    
    Args:
        text: Source text to generate questions from
        num_questions: Total number of questions to generate
        mix: Dictionary specifying question type distribution
             e.g., {"mcq": 6, "fill_blank": 2, "short_answer": 2}
    
    Returns:
        List of GeneratedQuestion objects
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
        
        question = _generate_mcq_question(concept, difficulty, i)
        questions.append(question)
    
    # Generate fill-in-the-blank questions
    for i in range(mix.get("fill_blank", 0)):
        concept = concepts[(i + mix["mcq"]) % len(concepts)]
        difficulty = difficulties[i % 3]
        
        question = _generate_fill_blank_question(concept, difficulty, i)
        questions.append(question)
    
    # Generate short answer questions
    for i in range(mix.get("short_answer", 0)):
        concept = concepts[(i + mix["mcq"] + mix["fill_blank"]) % len(concepts)]
        difficulty = difficulties[i % 3]
        
        question = _generate_short_answer_question(concept, difficulty, i)
        questions.append(question)
    
    return questions


# ============================================================================
# Question Generation Functions
# ============================================================================

def _generate_mcq_question(concept: str, difficulty: str, index: int) -> GeneratedQuestion:
    """Generate a multiple choice question."""
    prompts = {
        "easy": f"What is {concept}?",
        "medium": f"How does {concept} work in practice?",
        "hard": f"Analyze the implications of {concept} in real-world applications.",
    }
    
    # Create options (one correct, three incorrect)
    correct_option = MCQOption(
        text=f"{concept.capitalize()} is a fundamental concept that enables efficient processing",
        is_correct=True
    )
    
    incorrect_options = [
        MCQOption(text=f"{concept.capitalize()} is not related to the main topic", is_correct=False),
        MCQOption(text=f"{concept.capitalize()} has no practical applications", is_correct=False),
        MCQOption(text=f"{concept.capitalize()} is an outdated approach", is_correct=False),
    ]
    
    # Randomize option order (in production)
    options = [correct_option] + incorrect_options
    
    return GeneratedQuestion(
        type="mcq",
        prompt=prompts.get(difficulty, prompts["medium"]),
        options=options,
        answer=correct_option.text,
        explanation=f"The correct answer explains {concept} as discussed in the lecture material.",
        topic=concept,
        difficulty=difficulty,
    )


def _generate_fill_blank_question(concept: str, difficulty: str, index: int) -> GeneratedQuestion:
    """Generate a fill-in-the-blank question."""
    prompts = {
        "easy": f"The primary purpose of _____ is to process information efficiently.",
        "medium": f"In modern systems, _____ plays a crucial role in optimization.",
        "hard": f"Advanced applications leverage _____ to achieve superior performance.",
    }
    
    return GeneratedQuestion(
        type="fill_blank",
        prompt=prompts.get(difficulty, prompts["medium"]),
        options=None,
        answer=concept,
        explanation=f"The blank should be filled with '{concept}' based on the lecture content.",
        topic=concept,
        difficulty=difficulty,
    )


def _generate_short_answer_question(concept: str, difficulty: str, index: int) -> GeneratedQuestion:
    """Generate a short answer question."""
    prompts = {
        "easy": f"Describe {concept} in your own words.",
        "medium": f"Explain how {concept} is used in practical applications.",
        "hard": f"Critically evaluate the role of {concept} in solving complex problems.",
    }
    
    answers = {
        "easy": f"{concept} is a key concept",
        "medium": f"{concept} enables efficient processing",
        "hard": f"{concept} provides critical functionality",
    }
    
    return GeneratedQuestion(
        type="short_answer",
        prompt=prompts.get(difficulty, prompts["medium"]),
        options=None,
        answer=answers.get(difficulty, answers["medium"]),
        explanation=f"A good answer should demonstrate understanding of {concept} as covered in the lecture.",
        topic=concept,
        difficulty=difficulty,
    )


# ============================================================================
# Production-Ready AI Generation (Placeholder)
# ============================================================================

async def generate_questions_with_ai(text: str, num_questions: int = 10, api_key: Optional[str] = None):
    """
    Generate questions using OpenAI GPT-4 or similar LLM.
    
    This is a placeholder for production implementation.
    In production, you would:
    1. Use OpenAI API to analyze the text
    2. Generate high-quality, contextual questions
    3. Validate questions for quality and relevance
    
    Args:
        text: Source text
        num_questions: Number of questions to generate
        api_key: OpenAI API key
    
    Returns:
        List of GeneratedQuestion objects
    """
    # For now, fall back to template-based generation
    return await generate_questions_from_text(text, num_questions)