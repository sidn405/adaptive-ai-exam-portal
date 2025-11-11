from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json

class AnalyticsData:
    """Simple analytics data container."""
    def __init__(self, student_id: str, total_exams: int, average_score: float, 
                 time_per_question: float, difficulty_performance: Dict, 
                 topic_performance: Dict, improvement_trend: List):
        self.student_id = student_id
        self.total_exams = total_exams
        self.average_score = average_score
        self.time_per_question = time_per_question
        self.difficulty_performance = difficulty_performance
        self.topic_performance = topic_performance
        self.improvement_trend = improvement_trend

class AnalyticsEngine:
    def __init__(self):
        self.student_data = defaultdict(lambda: {
            "sessions": [],
            "scores": [],
            "time_data": [],
            "difficulty_performance": {"easy": [], "medium": [], "hard": []},
            "topic_performance": defaultdict(list)
        })
    
    def record_session(self, session, lecture):
        """Record a completed exam session for analytics."""
        student_id = session.learner_id
        if not student_id:
            return  # Skip if no learner ID
        
        score_percentage = (session.correct_count / session.total_answered * 100) if session.total_answered else 0
        
        self.student_data[student_id]["sessions"].append({
            "session_id": session.id,
            "date": session.completed_at or datetime.now(),
            "score": score_percentage,
            "lecture_id": session.lecture_id
        })
        
        self.student_data[student_id]["scores"].append(score_percentage)
        
        # Record time and performance data by difficulty and topic
        for answer in session.answers:
            # Find the question to get difficulty and topic
            question = next((q for q in lecture.questions if q.id == answer.question_id), None)
            if question:
                difficulty = answer.difficulty or question.difficulty or "medium"
                if difficulty in self.student_data[student_id]["difficulty_performance"]:
                    self.student_data[student_id]["difficulty_performance"][difficulty].append(
                        1.0 if answer.is_correct else 0.0
                    )
                
                if question.topic:
                    self.student_data[student_id]["topic_performance"][question.topic].append(
                        1.0 if answer.is_correct else 0.0
                    )
            
            # Record time data
            if answer.time_spent:
                self.student_data[student_id]["time_data"].append(answer.time_spent)
    
    def get_student_analytics(self, student_id: str):
        """Generate comprehensive analytics for a student."""
        data = self.student_data.get(student_id)
        
        if not data or not data["scores"]:
            return AnalyticsData(
                student_id=student_id,
                total_exams=0,
                average_score=0.0,
                time_per_question=0.0,
                difficulty_performance={},
                topic_performance={},
                improvement_trend=[]
            )
        
        # Calculate metrics
        total_exams = len(data["sessions"])
        average_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0.0
        
        # Time per question
        avg_time = sum(data["time_data"]) / len(data["time_data"]) if data["time_data"] else 45.0
        
        # Difficulty performance
        difficulty_performance = {}
        for difficulty, scores in data["difficulty_performance"].items():
            if scores:
                difficulty_performance[difficulty] = sum(scores) / len(scores) * 100
        
        # Topic performance
        topic_performance = {}
        for topic, scores in data["topic_performance"].items():
            if scores:
                topic_performance[topic] = sum(scores) / len(scores) * 100
        
        # Improvement trend (last 10 sessions)
        improvement_trend = data["scores"][-10:] if len(data["scores"]) >= 10 else data["scores"]
        
        return AnalyticsData(
            student_id=student_id,
            total_exams=total_exams,
            average_score=round(average_score, 2),
            time_per_question=round(avg_time, 1),
            difficulty_performance=difficulty_performance,
            topic_performance=topic_performance,
            improvement_trend=improvement_trend
        )
    
    def get_class_analytics(self) -> Dict:
        """Get analytics for all students (class overview)."""
        if not self.student_data:
            return {
                "total_students": 0,
                "total_exams": 0,
                "average_score": 0.0,
                "top_performers": [],
                "common_weak_topics": []
            }
        
        all_scores = []
        all_topics = defaultdict(list)
        student_averages = []
        
        for student_id, data in self.student_data.items():
            if data["scores"]:
                avg = sum(data["scores"]) / len(data["scores"])
                student_averages.append({"student_id": student_id, "average": avg})
                all_scores.extend(data["scores"])
                
                for topic, scores in data["topic_performance"].items():
                    all_topics[topic].extend(scores)
        
        # Top performers
        student_averages.sort(key=lambda x: x["average"], reverse=True)
        top_performers = student_averages[:5]
        
        # Weak topics
        weak_topics = []
        for topic, scores in all_topics.items():
            if scores:
                avg_performance = sum(scores) / len(scores) * 100
                if avg_performance < 60:
                    weak_topics.append({"topic": topic, "performance": round(avg_performance, 2)})
        
        weak_topics.sort(key=lambda x: x["performance"])
        
        return {
            "total_students": len(self.student_data),
            "total_exams": sum(len(data["sessions"]) for data in self.student_data.values()),
            "average_score": round(sum(all_scores) / len(all_scores), 2) if all_scores else 0.0,
            "top_performers": top_performers[:5],
            "common_weak_topics": weak_topics[:5]
        }
    
    def generate_recommendations(self, student_id: str) -> List[str]:
        """Generate personalized recommendations based on analytics."""
        analytics = self.get_student_analytics(student_id)
        recommendations = []
        
        if analytics.total_exams == 0:
            return ["Take your first exam to get personalized recommendations!"]
        
        # Score-based recommendations
        if analytics.average_score < 50:
            recommendations.append("Review lecture materials and focus on fundamental concepts.")
        elif analytics.average_score < 70:
            recommendations.append("Good progress! Practice more medium difficulty questions.")
        else:
            recommendations.append("Excellent performance! Challenge yourself with harder questions.")
        
        # Difficulty-based recommendations
        for difficulty, performance in analytics.difficulty_performance.items():
            if performance < 60:
                recommendations.append(f"Focus on {difficulty} level questions - current performance: {performance:.1f}%")
        
        # Topic-based recommendations
        weak_topics = [topic for topic, perf in analytics.topic_performance.items() if perf < 60]
        if weak_topics:
            recommendations.append(f"Review these topics: {', '.join(weak_topics[:3])}")
        
        return recommendations

# Global analytics engine instance
analytics_engine = AnalyticsEngine()