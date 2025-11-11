// No API_BASE needed - use relative URLs since frontend and backend are on same domain

// Global variables
let currentLecture = null;
let currentSession = null;
let currentQuestion = null;
let totalQuestions = 0;
let questionNumber = 1;

// Initialize proctoring when exam starts
let proctoringActive = false;
let tabSwitchCount = 0;

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

// Start exam with specific lecture
window.startExamWithLecture = async function(lectureId) {
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

// Upload lecture content
const uploadForm = document.getElementById('uploadForm');
if (uploadForm) {
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const title = document.getElementById('lectureTitle').value;
        const content = document.getElementById('lectureContent').value;
        const audioFile = document.getElementById('audioFile').files[0];
        
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const errorDiv = document.getElementById('lectureError');
        const successDiv = document.getElementById('lectureSuccess');
        
        // Hide previous messages
        if (errorDiv) errorDiv.classList.add('hidden');
        if (successDiv) successDiv.classList.add('hidden');
        
        submitBtn.disabled = true;
        submitBtn.textContent = 'Processing...';
        
        try {
            if (audioFile) {
                // Upload audio file for transcription
                const formData = new FormData();
                formData.append('file', audioFile);
                formData.append('title', title);
                
                const response = await fetch('/api/transcribe', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Transcription failed');
                }
                
                const data = await response.json();
                
                // Display transcript
                document.getElementById('lectureContent').value = data.transcript;
                
                const transcriptSuccess = document.getElementById('transcriptionSuccess');
                if (transcriptSuccess) transcriptSuccess.classList.remove('hidden');
                
                // Now create lecture with transcript
                const lectureFormData = new FormData();
                lectureFormData.append('title', title);
                lectureFormData.append('content', data.transcript);
                
                const lectureResponse = await fetch('/api/lectures', {
                    method: 'POST',
                    body: lectureFormData
                });
                
                if (!lectureResponse.ok) {
                    const error = await lectureResponse.json();
                    throw new Error(error.detail || 'Lecture creation failed');
                }
                
                const lectureData = await lectureResponse.json();
                
                if (successDiv) {
                    successDiv.textContent = `✓ Success! Created "${title}" with ${lectureData.total_questions} questions.`;
                    successDiv.classList.remove('hidden');
                }
                
                // Reload lectures list
                loadLectures();
                
            } else if (content) {
                // Text content - create lecture directly
                const formData = new FormData();
                formData.append('title', title);
                formData.append('content', content);
                
                const response = await fetch('/api/lectures', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Lecture creation failed');
                }
                
                const data = await response.json();
                
                if (successDiv) {
                    successDiv.textContent = `✓ Success! Created "${title}" with ${data.total_questions} questions.`;
                    successDiv.classList.remove('hidden');
                }
                
                // Reload lectures list
                loadLectures();
                
            } else {
                throw new Error('Please provide either text content or an audio file');
            }
            
        } catch (error) {
            console.error('Transcription error:', error);
            if (errorDiv) {
                errorDiv.textContent = 'Error: ' + error.message;
                errorDiv.classList.remove('hidden');
            }
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Generate Questions & Create Lecture';
        }
    });
}

// Audio file upload handler
const audioFileInput = document.getElementById('audioFile');
if (audioFileInput) {
    audioFileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        const fileNameSpan = document.getElementById('audioFileName');
        if (file && fileNameSpan) {
            fileNameSpan.textContent = file.name;
        }
    });
}

// Exam page - Load question
if (window.location.pathname === '/exam') {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session');
    
    if (sessionId) {
        currentSession = sessionId;
        proctoringActive = true;
        // Question loading handled by exam.html
    }
}

// Load and display current question
async function loadCurrentQuestion() {
    if (!currentQuestion) return;
    
    // Update progress
    const questionNumberEl = document.getElementById('questionNumber');
    const totalQuestionsEl = document.getElementById('totalQuestions');
    const progressBar = document.getElementById('progressBar');
    
    if (questionNumberEl) questionNumberEl.textContent = questionNumber;
    if (totalQuestionsEl) totalQuestionsEl.textContent = totalQuestions;
    
    // Update progress bar
    if (progressBar) {
        const progress = (questionNumber / totalQuestions) * 100;
        progressBar.style.width = `${progress}%`;
    }
    
    // Display question
    const questionContainer = document.getElementById('questionContainer');
    if (!questionContainer) return;
    
    questionContainer.innerHTML = '';
    
    // Question title
    const questionTitle = document.createElement('h3');
    questionTitle.textContent = `Question ${questionNumber} of ${totalQuestions}`;
    questionContainer.appendChild(questionTitle);
    
    // Difficulty badge
    if (currentQuestion.difficulty) {
        const badge = document.createElement('span');
        badge.className = `badge badge-${currentQuestion.difficulty}`;
        badge.textContent = currentQuestion.difficulty;
        questionContainer.appendChild(badge);
    }
    
    // Question prompt
    const questionText = document.createElement('p');
    questionText.className = 'question-text';
    questionText.textContent = currentQuestion.prompt || 'Question text';
    questionContainer.appendChild(questionText);
    
    // Render based on question type
    if (currentQuestion.type === 'mcq') {
        renderMCQ(currentQuestion, questionContainer);
    } else if (currentQuestion.type === 'fill_blank') {
        renderFillBlank(currentQuestion, questionContainer);
    } else if (currentQuestion.type === 'short_answer') {
        renderShortAnswer(currentQuestion, questionContainer);
    }
}

// Render MCQ question
function renderMCQ(question, container) {
    const optionsDiv = document.createElement('div');
    optionsDiv.className = 'options';
    
    if (question.options && Array.isArray(question.options)) {
        question.options.forEach((option, index) => {
            const optionDiv = document.createElement('div');
            optionDiv.className = 'option';
            optionDiv.innerHTML = `
                <input type="radio" name="answer" id="option${index}" value="${option.text}">
                <label for="option${index}">${option.text}</label>
            `;
            optionsDiv.appendChild(optionDiv);
        });
    }
    
    container.appendChild(optionsDiv);
    
    // Submit button
    const submitBtn = document.createElement('button');
    submitBtn.className = 'btn btn-primary';
    submitBtn.textContent = 'Submit Answer';
    submitBtn.onclick = submitAnswer;
    container.appendChild(submitBtn);
}

// Render fill in the blank
function renderFillBlank(question, container) {
    const input = document.createElement('input');
    input.type = 'text';
    input.id = 'answerInput';
    input.className = 'form-control';
    input.placeholder = 'Enter your answer';
    container.appendChild(input);
    
    const submitBtn = document.createElement('button');
    submitBtn.className = 'btn btn-primary';
    submitBtn.textContent = 'Submit Answer';
    submitBtn.onclick = submitAnswer;
    container.appendChild(submitBtn);
}

// Render short answer
function renderShortAnswer(question, container) {
    const textarea = document.createElement('textarea');
    textarea.id = 'answerInput';
    textarea.className = 'form-control';
    textarea.rows = 4;
    textarea.placeholder = 'Enter your answer';
    container.appendChild(textarea);
    
    const submitBtn = document.createElement('button');
    submitBtn.className = 'btn btn-primary';
    submitBtn.textContent = 'Submit Answer';
    submitBtn.onclick = submitAnswer;
    container.appendChild(submitBtn);
}

// Submit answer
async function submitAnswer() {
    let studentAnswer = null;
    
    if (currentQuestion.type === 'mcq') {
        const selected = document.querySelector('input[name="answer"]:checked');
        if (!selected) {
            alert('Please select an answer');
            return;
        }
        studentAnswer = selected.value;
    } else {
        const input = document.getElementById('answerInput');
        if (!input || !input.value.trim()) {
            alert('Please provide an answer');
            return;
        }
        studentAnswer = input.value.trim();
    }
    
    try {
        const response = await fetch(`/api/exams/${currentSession}/answer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question_id: currentQuestion.id,
                student_answer: studentAnswer,
                time_spent: 0
            })
        });
        
        if (!response.ok) throw new Error('Failed to submit answer');
        
        const data = await response.json();
        
        // Show result
        showResult(data.result);
        
        // Check if exam is complete
        if (data.exam_complete) {
            proctoringActive = false;
            setTimeout(() => {
                window.location.href = `/results?session=${currentSession}&score=${Math.round(data.final_score * 100)}`;
            }, 2000);
        } else {
            // Load next question
            currentQuestion = data.next_question;
            questionNumber++;
            setTimeout(loadCurrentQuestion, 2000);
        }
        
    } catch (error) {
        console.error('Error submitting answer:', error);
        alert('Error submitting answer: ' + error.message);
    }
}

// Show result feedback
function showResult(result) {
    const resultDiv = document.createElement('div');
    resultDiv.className = `result ${result.correct ? 'correct' : 'incorrect'}`;
    resultDiv.innerHTML = `
        <h3>${result.correct ? '✓ Correct!' : '✗ Incorrect'}</h3>
        <p><strong>Correct Answer:</strong> ${result.correct_answer}</p>
        ${result.explanation ? `<p><strong>Explanation:</strong> ${result.explanation}</p>` : ''}
        <p><strong>Current Score:</strong> ${Math.round(result.score * 100)}%</p>
    `;
    
    const container = document.getElementById('questionContainer');
    if (container) container.appendChild(resultDiv);
}