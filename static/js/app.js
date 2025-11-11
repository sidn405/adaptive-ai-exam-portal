// API Base URL
const API_BASE = window.location.origin + '/api';

// Proctoring Manager
class ProctoringManager {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.isActive = false;
        this.videoStream = null;
        this.tabSwitchCount = 0;
        this.detectionInterval = null;
    }

    async start() {
        this.isActive = true;
        await this.initWebcam();
        this.startTabSwitchDetection();
        this.updateStatus('active');
    }

    async initWebcam() {
        try {
            this.videoStream = await navigator.mediaDevices.getUserMedia({ 
                video: true, 
                audio: false 
            });
            
            const videoElement = document.getElementById('webcam-preview');
            if (videoElement) {
                videoElement.srcObject = this.videoStream;
            }
        } catch (error) {
            console.error('Webcam access denied:', error);
            this.logEvent('face_not_detected', 0.9, { reason: 'camera_access_denied' });
        }
    }

    startTabSwitchDetection() {
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && this.isActive) {
                this.tabSwitchCount++;
                this.logEvent('tab_switch', 1.0, { count: this.tabSwitchCount });
                this.updateStatus(this.tabSwitchCount > 3 ? 'danger' : 'warning');
                this.showAlert(`Tab switch detected (${this.tabSwitchCount})`, 'warning');
            }
        });

        // Prevent right-click
        document.addEventListener('contextmenu', (e) => {
            if (this.isActive) {
                e.preventDefault();
                this.showAlert('Right-click is disabled during the exam', 'warning');
            }
        });

        // Detect keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (this.isActive && (e.ctrlKey || e.metaKey)) {
                if (e.key === 'c' || e.key === 'v' || e.key === 'x') {
                    e.preventDefault();
                    this.showAlert('Copy/paste is disabled during the exam', 'warning');
                }
            }
        });
    }

    async logEvent(eventType, confidence, details = {}) {
        try {
            await fetch(`${API_BASE}/proctoring/${this.sessionId}/event`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    event_type: eventType,
                    timestamp: new Date().toISOString(),
                    confidence: confidence,
                    details: details
                })
            });
        } catch (error) {
            console.error('Error logging proctoring event:', error);
        }
    }

    updateStatus(status) {
        const indicator = document.querySelector('.status-indicator');
        if (indicator) {
            indicator.className = `status-indicator status-${status}`;
        }
    }

    showAlert(message, type = 'warning') {
        const alertsContainer = document.getElementById('proctoring-alerts');
        if (alertsContainer) {
            const alert = document.createElement('div');
            alert.className = `alert alert-${type}`;
            alert.textContent = message;
            alertsContainer.appendChild(alert);
            
            setTimeout(() => alert.remove(), 5000);
        }
    }

    stop() {
        this.isActive = false;
        if (this.videoStream) {
            this.videoStream.getTracks().forEach(track => track.stop());
        }
        if (this.detectionInterval) {
            clearInterval(this.detectionInterval);
        }
    }
}

// Exam Manager
class ExamManager {
    constructor() {
        this.sessionId = null;
        this.currentQuestion = null;
        this.questionIndex = 0;
        this.totalQuestions = 0;
        this.startTime = null;
        this.proctoring = null;
    }

    async startExam(studentId, lectureId) {
        try {
            const response = await fetch(`${API_BASE}/exams/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ student_id: studentId, lecture_id: lectureId })
            });

            const data = await response.json();
            this.sessionId = data.session_id;
            this.totalQuestions = data.total_questions;
            this.currentQuestion = data.first_question;
            this.startTime = Date.now();

            // Start proctoring
            this.proctoring = new ProctoringManager(this.sessionId);
            await this.proctoring.start();

            this.displayQuestion();
            this.updateProgress();
        } catch (error) {
            console.error('Error starting exam:', error);
            alert('Failed to start exam. Please try again.');
        }
    }

    displayQuestion() {
        const container = document.getElementById('question-container');
        if (!container || !this.currentQuestion) return;

        const difficultyClass = `difficulty-${this.currentQuestion.difficulty}`;
        
        let optionsHtml = '';
        if (this.currentQuestion.options) {
            optionsHtml = this.currentQuestion.options.map((option, idx) => `
                <div class="option" onclick="examManager.selectOption('${option}')" data-option="${option}">
                    ${option}
                </div>
            `).join('');
        } else {
            optionsHtml = `
                <textarea 
                    id="short-answer" 
                    class="form-textarea" 
                    placeholder="Enter your answer here..."
                ></textarea>
            `;
        }

        container.innerHTML = `
            <div class="question-card">
                <div class="question-header">
                    <span class="question-number">Question ${this.questionIndex + 1} of ${this.totalQuestions}</span>
                    <span class="difficulty-badge ${difficultyClass}">${this.currentQuestion.difficulty}</span>
                </div>
                <div class="question-text">${this.currentQuestion.question_text}</div>
                <div class="options">${optionsHtml}</div>
                <button class="btn btn-primary" onclick="examManager.submitAnswer()" style="margin-top: 20px;">
                    Submit Answer
                </button>
            </div>
        `;
    }

    selectOption(option) {
        document.querySelectorAll('.option').forEach(el => el.classList.remove('selected'));
        event.target.classList.add('selected');
        this.selectedAnswer = option.charAt(0);  // Get the letter (A, B, C, D)
    }

    async submitAnswer() {
        let answer;
        if (this.currentQuestion.question_type === 'short_answer') {
            answer = document.getElementById('short-answer')?.value;
        } else {
            answer = this.selectedAnswer;
        }

        if (!answer) {
            alert('Please select or enter an answer');
            return;
        }

        const timeSpent = Math.floor((Date.now() - this.startTime) / 1000);

        try {
            const response = await fetch(`${API_BASE}/exams/${this.sessionId}/answer`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question_id: this.currentQuestion.id,
                    student_answer: answer,
                    time_spent: timeSpent
                })
            });

            const data = await response.json();
            
            this.showFeedback(data.result);

            if (data.exam_complete) {
                setTimeout(() => {
                    this.endExam(data.final_score);
                }, 2000);
            } else {
                setTimeout(() => {
                    this.currentQuestion = data.next_question;
                    this.questionIndex++;
                    this.startTime = Date.now();
                    this.selectedAnswer = null;
                    this.displayQuestion();
                    this.updateProgress();
                }, 2000);
            }
        } catch (error) {
            console.error('Error submitting answer:', error);
            alert('Failed to submit answer. Please try again.');
        }
    }

    showFeedback(result) {
        const container = document.getElementById('question-container');
        const feedbackClass = result.is_correct ? 'correct' : 'incorrect';
        const feedbackIcon = result.is_correct ? '✓' : '✗';
        
        container.innerHTML = `
            <div class="card result-item ${feedbackClass}">
                <h2>${feedbackIcon} ${result.is_correct ? 'Correct!' : 'Incorrect'}</h2>
                <p><strong>Score:</strong> ${result.score.toFixed(2)} points</p>
                <p>${result.feedback}</p>
                <p><strong>Next difficulty:</strong> ${result.next_difficulty}</p>
            </div>
        `;
    }

    updateProgress() {
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        
        if (progressFill && progressText) {
            const percentage = ((this.questionIndex + 1) / this.totalQuestions) * 100;
            progressFill.style.width = `${percentage}%`;
            progressText.textContent = `${this.questionIndex + 1} / ${this.totalQuestions} questions`;
        }
    }

    endExam(finalScore) {
        if (this.proctoring) {
            this.proctoring.stop();
        }
        
        window.location.href = `/results?session=${this.sessionId}`;
    }
}

// Analytics Manager
class AnalyticsManager {
    async loadStudentAnalytics(studentId) {
        try {
            const response = await fetch(`${API_BASE}/analytics/${studentId}`);
            const data = await response.json();
            this.displayAnalytics(data);
        } catch (error) {
            console.error('Error loading analytics:', error);
        }
    }

    displayAnalytics(data) {
        const container = document.getElementById('analytics-container');
        if (!container) return;

        const analytics = data.analytics;
        
        container.innerHTML = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">${analytics.total_exams}</div>
                    <div class="stat-label">Total Exams</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${analytics.average_score.toFixed(1)}%</div>
                    <div class="stat-label">Average Score</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${Math.floor(analytics.time_per_question)}s</div>
                    <div class="stat-label">Avg Time/Question</div>
                </div>
            </div>

            <div class="card">
                <h3 class="card-header">Performance by Difficulty</h3>
                <div id="difficulty-chart"></div>
            </div>

            <div class="card">
                <h3 class="card-header">Performance by Topic</h3>
                <div id="topic-chart"></div>
            </div>

            <div class="card">
                <h3 class="card-header">Recommendations</h3>
                <ul>
                    ${data.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                </ul>
            </div>
        `;

        this.renderCharts(analytics);
    }

    renderCharts(analytics) {
        // Simple bar chart rendering (you can replace with Chart.js)
        const difficultyContainer = document.getElementById('difficulty-chart');
        if (difficultyContainer && analytics.difficulty_performance) {
            let chartHtml = '';
            for (const [difficulty, score] of Object.entries(analytics.difficulty_performance)) {
                chartHtml += `
                    <div style="margin: 10px 0;">
                        <strong>${difficulty}:</strong>
                        <div style="background: #e5e7eb; height: 30px; border-radius: 4px; overflow: hidden;">
                            <div style="background: #4F46E5; height: 100%; width: ${score}%;"></div>
                        </div>
                        <span>${score.toFixed(1)}%</span>
                    </div>
                `;
            }
            difficultyContainer.innerHTML = chartHtml;
        }

        const topicContainer = document.getElementById('topic-chart');
        if (topicContainer && analytics.topic_performance) {
            let chartHtml = '';
            for (const [topic, score] of Object.entries(analytics.topic_performance)) {
                chartHtml += `
                    <div style="margin: 10px 0;">
                        <strong>${topic}:</strong>
                        <div style="background: #e5e7eb; height: 30px; border-radius: 4px; overflow: hidden;">
                            <div style="background: #10B981; height: 100%; width: ${score}%;"></div>
                        </div>
                        <span>${score.toFixed(1)}%</span>
                    </div>
                `;
            }
            topicContainer.innerHTML = chartHtml;
        }
    }
}

// Global instances
let examManager = new ExamManager();
let analyticsManager = new AnalyticsManager();

// Utility functions
function generateStudentId() {
    return 'student_' + Math.random().toString(36).substr(2, 9);
}

async function loadResults(sessionId) {
    try {
        const response = await fetch(`${API_BASE}/results/${sessionId}`);
        const data = await response.json();
        displayResults(data);
    } catch (error) {
        console.error('Error loading results:', error);
    }
}

function displayResults(data) {
    const container = document.getElementById('results-container');
    if (!container) return;

    const scorePercentage = data.final_score.percentage;
    const scoreClass = scorePercentage >= 80 ? 'success' : scorePercentage >= 60 ? 'warning' : 'danger';

    container.innerHTML = `
        <div class="results-header">
            <h1>Exam Results</h1>
            <div class="score-display">${scorePercentage}%</div>
            <p>You scored ${data.final_score.correct} out of ${data.final_score.total_questions} correct</p>
        </div>

        <div class="score-breakdown">
            <div class="stat-card">
                <div class="stat-value">${data.final_score.score}</div>
                <div class="stat-label">Total Points</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.proctoring.integrity_score}</div>
                <div class="stat-label">Integrity Score</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.proctoring.risk_level.toUpperCase()}</div>
                <div class="stat-label">Risk Level</div>
            </div>
        </div>

        <div class="card">
            <h3 class="card-header">Question Review</h3>
            ${data.results.map((result, idx) => `
                <div class="result-item ${result.is_correct ? 'correct' : 'incorrect'}">
                    <p><strong>Q${idx + 1}:</strong> ${result.question}</p>
                    <p><strong>Your Answer:</strong> ${result.your_answer}</p>
                    ${!result.is_correct ? `<p><strong>Correct Answer:</strong> ${result.correct_answer}</p>` : ''}
                    <p><em>${result.feedback}</em></p>
                </div>
            `).join('')}
        </div>

        <div class="card">
            <h3 class="card-header">Proctoring Summary</h3>
            <p><strong>Duration:</strong> ${Math.floor(data.proctoring.duration / 60)} minutes</p>
            <p><strong>Tab Switches:</strong> ${data.proctoring.event_summary.tab_switches}</p>
            <p><strong>Total Events:</strong> ${data.proctoring.total_events}</p>
            <h4>Recommendations:</h4>
            <ul>
                ${data.proctoring.recommendations.map(rec => `<li>${rec}</li>`).join('')}
            </ul>
        </div>

        <div style="text-align: center; margin-top: 30px;">
            <a href="/" class="btn btn-primary">Back to Home</a>
            <a href="/analytics?student=${data.student_id}" class="btn btn-secondary">View Analytics</a>
        </div>
    `;
}