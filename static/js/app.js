// Global variables
let currentLecture = null;
let currentSession = null;
let currentQuestion = null;
let totalQuestions = 0;
let questionNumber = 1;

// Initialize proctoring when exam starts
let proctoringActive = false;
let tabSwitchCount = 0;

// Exam Manager object
const examManager = {
    currentSession: null,
    sessionId: null,
    currentQuestion: null,
    questionNumber: 1,
    totalQuestions: 0,
    
    async startExam(studentId, lectureId) {
        try {
            const response = await fetch('/api/exams/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_id: studentId,
                    lecture_id: lectureId
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to start exam');
            }
            
            const data = await response.json();
            this.sessionId = data.session_id;
            this.currentSession = data.session_id;
            currentSession = data.session_id;
            proctoringActive = true;
            
            await this.initializeWebcam();
            await this.loadQuestion();
            
        } catch (error) {
            console.error('Error starting exam:', error);
            alert('Error starting exam: ' + error.message);
            window.location.href = '/';
        }
    },
    
    async initializeWebcam() {
        try {
            const video = document.getElementById('webcam-preview');
            if (!video) return;
            
            const stream = await navigator.mediaDevices.getUserMedia({ 
                video: true, 
                audio: false 
            });
            video.srcObject = stream;
        } catch (error) {
            console.error('Webcam error:', error);
            const alertsDiv = document.getElementById('proctoring-alerts');
            if (alertsDiv) {
                alertsDiv.innerHTML = `
                    <div style="padding: 8px; background: #FEE2E2; color: #991B1B; border-radius: 4px; font-size: 0.875rem;">
                        ⚠️ Webcam access denied. Proctoring may be limited.
                    </div>
                `;
            }
        }
    },
    
    async initialize(sessionId) {
        this.sessionId = sessionId;
        this.currentSession = sessionId;
        currentSession = sessionId;
        proctoringActive = true;
        await this.initializeWebcam();
        await this.loadQuestion();
    },
    
    async loadQuestion() {
        try {
            const response = await fetch(`/api/exams/${this.sessionId}/question`);
            if (!response.ok) throw new Error('Failed to load question');
            
            const data = await response.json();
            this.currentQuestion = data.question;
            currentQuestion = data.question;
            this.totalQuestions = data.total_questions || 10;
            totalQuestions = this.totalQuestions;
            
            this.displayQuestion();
        } catch (error) {
            console.error('Error loading question:', error);
            alert('Error loading question: ' + error.message);
        }
    },
    
    displayQuestion() {
        if (!this.currentQuestion) return;
        
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        
        const progress = (this.questionNumber / this.totalQuestions) * 100;
        if (progressFill) progressFill.style.width = `${progress}%`;
        if (progressText) progressText.textContent = `Question ${this.questionNumber} / ${this.totalQuestions}`;
        
        const container = document.getElementById('question-container');
        if (!container) return;
        
        let questionHTML = `
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="margin: 0;">Question ${this.questionNumber}</h2>
                    <span class="badge badge-${this.currentQuestion.difficulty || 'medium'}">
                        ${this.currentQuestion.difficulty || 'Medium'}
                    </span>
                </div>
                <p style="font-size: 1.25rem; margin-bottom: 30px; line-height: 1.6;">
                    ${this.currentQuestion.prompt || this.currentQuestion.question || 'Question text'}
                </p>
        `;
        
        if (this.currentQuestion.type === 'mcq' || this.currentQuestion.type === 'multiple_choice') {
            questionHTML += this.renderMCQ();
        } else if (this.currentQuestion.type === 'fill_blank' || this.currentQuestion.type === 'fill_in_blank') {
            questionHTML += this.renderFillBlank();
        } else if (this.currentQuestion.type === 'short_answer') {
            questionHTML += this.renderShortAnswer();
        } else {
            questionHTML += this.renderShortAnswer();
        }
        
        questionHTML += `
                <button class="btn btn-primary" onclick="examManager.submitCurrentAnswer()" style="margin-top: 20px;">
                    Submit Answer
                </button>
            </div>
        `;
        
        container.innerHTML = questionHTML;
    },
    
    renderMCQ() {
        const options = this.currentQuestion.options || this.currentQuestion.choices || [];
        return `
            <div style="display: flex; flex-direction: column; gap: 12px;">
                ${options.map((option, index) => {
                    const optionText = typeof option === 'string' ? option : (option.text || option.option || '');
                    return `
                        <label class="option-label" style="display: flex; align-items: center; padding: 16px; border: 2px solid var(--border-color); border-radius: 8px; cursor: pointer; transition: all 0.2s;">
                            <input type="radio" name="answer" value="${optionText}" style="margin-right: 12px; width: 20px; height: 20px;">
                            <span style="flex: 1;">${optionText}</span>
                        </label>
                    `;
                }).join('')}
            </div>
        `;
    },
    
    renderFillBlank() {
        return `
            <input 
                type="text" 
                id="answer-input" 
                class="form-input" 
                placeholder="Enter your answer"
                style="font-size: 1.125rem; padding: 16px;"
            >
        `;
    },
    
    renderShortAnswer() {
        return `
            <textarea 
                id="answer-input" 
                class="form-textarea" 
                placeholder="Enter your answer here..."
                rows="6"
                style="font-size: 1.125rem; padding: 16px;"
            ></textarea>
        `;
    },
    
    async submitCurrentAnswer() {
        let studentAnswer = null;
        
        if (this.currentQuestion.type === 'mcq' || this.currentQuestion.type === 'multiple_choice') {
            const selected = document.querySelector('input[name="answer"]:checked');
            if (!selected) {
                alert('Please select an answer');
                return;
            }
            studentAnswer = selected.value;
        } else {
            const input = document.getElementById('answer-input');
            if (!input || !input.value.trim()) {
                alert('Please provide an answer');
                return;
            }
            studentAnswer = input.value.trim();
        }
        
        try {
            const response = await fetch(`/api/exams/${this.sessionId}/answer`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question_id: this.currentQuestion.id,
                    student_answer: studentAnswer,
                    time_spent: 0
                })
            });
            
            if (!response.ok) throw new Error('Failed to submit answer');
            
            const data = await response.json();
            this.showFeedback(data);
            
            if (data.exam_complete) {
                proctoringActive = false;
                setTimeout(() => {
                    window.location.href = `/results?session=${this.sessionId}&score=${Math.round((data.final_score || 0) * 100)}`;
                }, 3000);
            } else {
                this.questionNumber++;
                setTimeout(() => this.loadQuestion(), 3000);
            }
            
        } catch (error) {
            console.error('Error submitting answer:', error);
            alert('Error submitting answer: ' + error.message);
        }
    },
    
    showFeedback(data) {
        const container = document.getElementById('question-container');
        if (!container) return;
        
        const isCorrect = data.correct || data.result?.correct || false;
        const correctAnswer = data.correct_answer || data.result?.correct_answer || 'N/A';
        const explanation = data.explanation || data.result?.explanation || '';
        const score = data.score || data.result?.score || 0;
        
        const feedbackHTML = `
            <div class="card" style="background: ${isCorrect ? '#D1FAE5' : '#FEE2E2'}; border-left: 4px solid ${isCorrect ? '#10B981' : '#EF4444'};">
                <h2 style="color: ${isCorrect ? '#065F46' : '#991B1B'}; margin-bottom: 16px;">
                    ${isCorrect ? '✓ Correct!' : '✗ Incorrect'}
                </h2>
                <p style="margin-bottom: 12px;">
                    <strong>Correct Answer:</strong> ${correctAnswer}
                </p>
                ${explanation ? `<p style="margin-bottom: 12px;"><strong>Explanation:</strong> ${explanation}</p>` : ''}
                <p style="font-size: 1.25rem; font-weight: 600;">
                    Current Score: ${Math.round(score * 100)}%
                </p>
            </div>
        `;
        
        container.innerHTML = feedbackHTML;
    }
};

// Tab switching detection
document.addEventListener('visibilitychange', () => {
    if (document.hidden && proctoringActive && currentSession) {
        tabSwitchCount++;
        logProctoringEvent('tab_switch', 1.0, { count: tabSwitchCount });
    }
});

// Log proctoring event
async function logProctoringEvent(eventType, confidence, details = {}) {
    if (!currentSession) return;
    
    try {
        await fetch(`/api/lectures/proctoring/${currentSession}/event`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSession,
                event_type: eventType,
                timestamp: new Date().toISOString(),
                confidence: confidence,
                details: details
            })
        });
    } catch (error) {
        console.error('Proctoring event error:', error);
    }
}

// Load lectures on page load
window.addEventListener('DOMContentLoaded', () => {
    loadLectures();
});

// Load available lectures
async function loadLectures() {
    try {
        const response = await fetch('/api/lectures');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const lectures = await response.json();
        
        const container = document.getElementById('lecturesContainer');
        if (!container) return;
        
        if (lectures.length === 0) {
            container.innerHTML = '<p>No lectures available. Create one above to get started!</p>';
            return;
        }
        
        container.innerHTML = lectures.map(lecture => `
            <div class="lecture-card">
                <h3>${lecture.title}</h3>
                <p>${lecture.summary || 'No summary'}</p>
                <p><strong>Questions:</strong> ${lecture.question_count}</p>
                <button class="btn btn-primary" onclick="startExamWithLecture('${lecture.id}')">
                    Take Exam
                </button>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading lectures:', error);
        const container = document.getElementById('lecturesContainer');
        if (container) {
            container.innerHTML = '<p>Error loading lectures. Please refresh the page.</p>';
        }
    }
}

// Start exam for a specific lecture
window.startExamForLecture = async function(lectureId) {
    const studentId = prompt('Enter your student ID:');
    if (!studentId) return;
    
    try {
        const response = await fetch('/api/exams/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_id: studentId,
                lecture_id: lectureId
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start exam');
        }
        
        const data = await response.json();
        window.location.href = `/exam?session=${data.session_id}`;
        
    } catch (error) {
        console.error('Error starting exam:', error);
        alert('Error starting exam: ' + error.message);
    }
}

// Exam page initialization
if (window.location.pathname === '/exam') {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session');
    const lectureId = urlParams.get('lecture');
    const studentId = urlParams.get('student');
    
    if (sessionId) {
        currentSession = sessionId;
        proctoringActive = true;
        examManager.initialize(sessionId);
    } else if (lectureId && studentId) {
        examManager.startExam(studentId, lectureId);
    }
}