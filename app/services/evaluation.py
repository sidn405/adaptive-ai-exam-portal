from typing import Dict, List
from app.models import Question, Answer, EvaluationResult, DifficultyLevel
import difflib

class SmartEvaluator:
    def __init__(self):
        self.difficulty_thresholds = {
            DifficultyLevel.EASY: 0.7,
            DifficultyLevel.MEDIUM: 0.6,
            DifficultyLevel.HARD: 0.5
        }
    
    def evaluate_answer(self, question: Question, answer: Answer, current_difficulty: DifficultyLevel) -> EvaluationResult:
        """
        Evaluate a student's answer and determine next difficulty level.
        """
        is_correct = self._check_answer(question, answer.student_answer)
        score = self._calculate_score(question, answer, is_correct)
        feedback = self._generate_feedback(question, answer, is_correct)
        next_difficulty = self._determine_next_difficulty(is_correct, current_difficulty, answer.time_spent)
        
        return EvaluationResult(
            question_id=question.id,
            is_correct=is_correct,
            score=score,
            feedback=feedback,
            next_difficulty=next_difficulty
        )
    
    def _check_answer(self, question: Question, student_answer: str) -> bool:
        """Check if answer is correct."""
        if question.question_type == "mcq" or question.question_type == "true_false":
            return student_answer.strip().upper() == question.correct_answer.strip().upper()
        else:
            # For short answers, use similarity matching
            similarity = difflib.SequenceMatcher(None, 
                student_answer.lower().strip(), 
                question.correct_answer.lower().strip()
            ).ratio()
            return similarity > 0.7
    
    def _calculate_score(self, question: Question, answer: Answer, is_correct: bool) -> float:
        """Calculate score based on correctness, difficulty, and time spent."""
        if not is_correct:
            return 0.0
        
        base_score = {
            DifficultyLevel.EASY: 1.0,
            DifficultyLevel.MEDIUM: 1.5,
            DifficultyLevel.HARD: 2.0
        }[question.difficulty]
        
        # Time bonus (faster answers get slight bonus)
        expected_time = 60  # 60 seconds expected
        time_factor = max(0.8, min(1.2, expected_time / max(answer.time_spent, 10)))
        
        return base_score * time_factor
    
    def _generate_feedback(self, question: Question, answer: Answer, is_correct: bool) -> str:
        """Generate personalized feedback."""
        if is_correct:
            if answer.time_spent < 30:
                return f"Excellent! Quick and accurate. {question.explanation}"
            else:
                return f"Correct! {question.explanation}"
        else:
            return f"Incorrect. {question.explanation} Review this concept for better understanding."
    
    def _determine_next_difficulty(self, is_correct: bool, current_difficulty: DifficultyLevel, time_spent: int) -> DifficultyLevel:
        """Adaptive logic to determine next question difficulty."""
        difficulties = [DifficultyLevel.EASY, DifficultyLevel.MEDIUM, DifficultyLevel.HARD]
        current_index = difficulties.index(current_difficulty)
        
        if is_correct and time_spent < 45:
            # Answer was correct and quick - increase difficulty
            new_index = min(current_index + 1, len(difficulties) - 1)
        elif is_correct and time_spent < 90:
            # Answer was correct but took time - keep same difficulty
            new_index = current_index
        elif not is_correct and current_index > 0:
            # Answer was incorrect - decrease difficulty
            new_index = current_index - 1
        else:
            # Keep same difficulty
            new_index = current_index
        
        return difficulties[new_index]

class AdaptiveTestEngine:
    def __init__(self):
        self.evaluator = SmartEvaluator()
        self.performance_history = {}
    
    def select_next_question(self, questions: List[Question], answered_ids: List[str], 
                           current_difficulty: DifficultyLevel) -> Question:
        """Select next question based on adaptive logic."""
        available_questions = [q for q in questions if q.id not in answered_ids]
        
        # Filter by current difficulty
        difficulty_questions = [q for q in available_questions if q.difficulty == current_difficulty]
        
        if difficulty_questions:
            return difficulty_questions[0]
        elif available_questions:
            return available_questions[0]
        else:
            return None
    
    def calculate_final_score(self, results: List[EvaluationResult]) -> Dict:
        """Calculate comprehensive final score and analytics."""
        if not results:
            return {"score": 0, "percentage": 0, "total_questions": 0}
        
        total_score = sum(r.score for r in results)
        correct_count = sum(1 for r in results if r.is_correct)
        total_questions = len(results)
        
        return {
            "score": round(total_score, 2),
            "percentage": round((correct_count / total_questions) * 100, 2),
            "correct": correct_count,
            "total_questions": total_questions,
            "difficulty_breakdown": self._get_difficulty_breakdown(results)
        }
    
    def _get_difficulty_breakdown(self, results: List[EvaluationResult]) -> Dict:
        """Analyze performance by difficulty level."""
        breakdown = {
            "easy": {"correct": 0, "total": 0},
            "medium": {"correct": 0, "total": 0},
            "hard": {"correct": 0, "total": 0}
        }
        
        # This would need to track difficulty per question in production
        return breakdown