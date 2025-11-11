from typing import List, Dict
from datetime import datetime
from app.models import ProctoringEvent
import uuid

# In-memory storage for proctoring events
PROCTORING_EVENTS: List[Dict] = []

class ProctoringEngine:
    def __init__(self):
        self.sessions = {}
        self.risk_thresholds = {
            "tab_switch": 3,
            "face_not_detected": 5,
            "multiple_faces": 1,
            "suspicious_object": 2
        }
    
    def start_proctoring_session(self, session_id: str) -> Dict:
        """Initialize proctoring for an exam session."""
        self.sessions[session_id] = {
            "started_at": datetime.now(),
            "events": [],
            "flags": {
                "tab_switch": 0,
                "face_not_detected": 0,
                "multiple_faces": 0,
                "suspicious_object": 0
            },
            "risk_level": "low"
        }
        return {"status": "proctoring_started", "session_id": session_id}
    
    def log_proctoring_event(self, event: ProctoringEvent) -> Dict:
        """Log a proctoring event and update risk assessment."""
        session_id = event.session_id
        
        if session_id not in self.sessions:
            return {"error": "Session not found"}
        
        # Record the event
        self.sessions[session_id]["events"].append({
            "type": event.event_type,
            "timestamp": event.timestamp,
            "confidence": event.confidence,
            "details": event.details
        })
        
        # Update flag counts
        if event.event_type in self.sessions[session_id]["flags"]:
            self.sessions[session_id]["flags"][event.event_type] += 1
        
        # Assess risk level
        risk_level = self._assess_risk_level(session_id)
        self.sessions[session_id]["risk_level"] = risk_level
        
        return {
            "status": "event_logged",
            "current_risk_level": risk_level,
            "flags": self.sessions[session_id]["flags"]
        }
    
    def _assess_risk_level(self, session_id: str) -> str:
        """Assess the overall risk level for a proctoring session."""
        flags = self.sessions[session_id]["flags"]
        
        # Calculate risk score
        risk_score = 0
        for event_type, count in flags.items():
            threshold = self.risk_thresholds.get(event_type, 5)
            if count > threshold:
                risk_score += (count - threshold) * 2
            else:
                risk_score += count * 0.5
        
        # Determine risk level
        if risk_score < 5:
            return "low"
        elif risk_score < 10:
            return "medium"
        else:
            return "high"
    
    def get_proctoring_report(self, session_id: str) -> Dict:
        """Generate a comprehensive proctoring report for a session."""
        if session_id not in self.sessions:
            return {"error": "Session not found"}
        
        session_data = self.sessions[session_id]
        
        # Categorize events
        event_summary = {
            "tab_switches": len([e for e in session_data["events"] if e["type"] == "tab_switch"]),
            "face_detection_issues": len([e for e in session_data["events"] if e["type"] == "face_not_detected"]),
            "multiple_faces_detected": len([e for e in session_data["events"] if e["type"] == "multiple_faces"]),
            "suspicious_objects": len([e for e in session_data["events"] if e["type"] == "suspicious_object"]),
        }
        
        # Generate integrity score (0-100)
        integrity_score = self._calculate_integrity_score(session_data)
        
        # Generate recommendations
        recommendations = self._generate_proctoring_recommendations(session_data)
        
        return {
            "session_id": session_id,
            "duration": (datetime.now() - session_data["started_at"]).seconds,
            "risk_level": session_data["risk_level"],
            "integrity_score": integrity_score,
            "event_summary": event_summary,
            "total_events": len(session_data["events"]),
            "flags": session_data["flags"],
            "recommendations": recommendations,
            "detailed_events": session_data["events"][-10:]  # Last 10 events
        }
    
    def _calculate_integrity_score(self, session_data: Dict) -> int:
        """Calculate an integrity score from 0-100 based on proctoring data."""
        base_score = 100
        flags = session_data["flags"]
        
        # Deduct points based on violations
        deductions = {
            "tab_switch": 5,
            "face_not_detected": 10,
            "multiple_faces": 20,
            "suspicious_object": 15
        }
        
        for flag_type, count in flags.items():
            deduction = deductions.get(flag_type, 5) * count
            base_score -= deduction
        
        return max(0, min(100, base_score))
    
    def _generate_proctoring_recommendations(self, session_data: Dict) -> List[str]:
        """Generate recommendations based on proctoring results."""
        recommendations = []
        flags = session_data["flags"]
        risk_level = session_data["risk_level"]
        
        if risk_level == "high":
            recommendations.append("⚠️ High risk detected - Manual review recommended")
        
        if flags["tab_switch"] > self.risk_thresholds["tab_switch"]:
            recommendations.append(f"Excessive tab switching detected ({flags['tab_switch']} times)")
        
        if flags["face_not_detected"] > self.risk_thresholds["face_not_detected"]:
            recommendations.append("Student was frequently not visible on camera")
        
        if flags["multiple_faces"] > 0:
            recommendations.append("Multiple faces detected - possible unauthorized assistance")
        
        if flags["suspicious_object"] > 0:
            recommendations.append("Suspicious objects detected in frame")
        
        if not recommendations:
            recommendations.append("✓ No significant integrity concerns detected")
        
        return recommendations

# Global proctoring engine instance
proctoring_engine = ProctoringEngine()