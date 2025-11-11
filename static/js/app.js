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
        console.error('Error logging proctoring event:', error);
    }
}

// Upload lecture content
document.getElementById('uploadForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const title = document.getElementById('lectureTitle').value;
    const content = document.getElementById('lectureContent').value;
    const audioFile = document.getElementById('audioFile').files[0];
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing...';
    
    try {
        let response;
        
        if (audioFile) {
            // Upload audio file
            const formData = new FormData();
            formData.append('file', audioFile);
            formData.append('title', title);
            
            response = await fetch('/api/transcribe', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) throw new Error('Transcription failed');
            
            const data = await response.json();
            
            // Display transcript
            document.getElementById('lectureContent').value = data.transcript;
            document.getElementById('transcriptionSuccess').classList.remove('hidden');
            
            currentLecture = {
                id: data.lecture_id,
                title: data.title,
                content: data.transcript
            };
            
            // Now generate questions
            await generateQuestions(data.lecture_id, data.transcript, title);
            
        } else if (content) {
            // Text content - create lecture and generate questions
            const formData = new FormData();
            formData.append('title', title);
            formData.append('content', content);
            
            response = await fetch('/api/lectures', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) throw new Error('Lecture creation failed');
            
            const data = await response.json();
            currentLecture = {
                id: data.lecture_id,
                title: data.title || title,
                content: content
            };
            
            document.getElementById('lectureSuccess').classList.remove('hidden');
            document.getElementById('startExamBtn').classList.remove('hidden');
            
        } else {
            alert('Please provide either text content or an audio file');
            return;
        }
        
    } catch (error) {
        console.error('Error:', error);
        alert('Error processing lecture: ' + error.message);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Generate Questions & Create Lecture';
    }
});

// Generate questions
async function generateQuestions(lectureId, content, title) {
    try {
        // Questions already generated in the POST /api/lectures call
        document.getElementById('lectureSuccess').classList.remove('hidden');
        document.getElementById('startExamBtn').classList.remove('hidden');
        
        currentLecture = {
            id: lectureId,
            title: title,
            content: content
        };
        
    } catch (error) {
        console.error('Error generating questions:', error);
        alert('Error generating questions');
    }
}

// Start exam
document.getElementById('startExamBtn')?.addEventListener('click', async () => {
    if (!currentLecture) {
        alert('Please create a lecture first');
        return;
    }
    
    const studentId = prompt('Enter your student ID:');
    if (!studentId) return;
    
    try {
        const response = await fetch('/api/exams/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_id: studentId,
                lecture_id: currentLecture.id
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start exam');
        }
        
        const data = await response.json();
        currentSession = data.session_id;
        totalQuestions = data.total_questions;
        currentQuestion = data.first_question;
        questionNumber = 1;
        
        // Start proctoring
        proctoringActive = true;
        
        // Redirect to exam page
        window.location.href = `/exam?session=${currentSession}`;
        
    } catch (error) {
        console.error('Error starting exam:', error);
        alert('Error starting exam: ' + error.message);
    }
});

// Exam page - Load question
if (window.location.pathname === '/exam') {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session');
    
    if (sessionId) {
        currentSession = sessionId;
        proctoringActive = true;
        loadCurrentQuestion();
    }
}

// Load and display current question
async function loadCurrentQuestion() {
    if (!currentQuestion) return;
    
    // Update progress
    document.getElementById('questionNumber').textContent = questionNumber;
    document.getElementById('totalQuestions').textContent = totalQuestions;
    
    // Update progress bar
    const progress = (questionNumber / totalQuestions) * 100;
    document.getElementById('progressBar').style.width = `${progress}%`;
    
    // Display question - FIX: Properly access question properties
    const questionContainer = document.getElementById('questionContainer');
    questionContainer.innerHTML = '';
    
    // Question text
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
    
    // Question prompt - FIX: Access .prompt property
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

// Render MCQ question - FIX: Properly access option.text
function renderMCQ(question, container) {
    const optionsDiv = document.createElement('div');
    optionsDiv.className = 'options';
    
    // FIX: Access options array and each option's text property
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
        if (!input.value.trim()) {
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
        alert('Error submitting answer');
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
    
    document.getElementById('questionContainer').appendChild(resultDiv);
}

// Audio file upload handler
document.getElementById('audioFile')?.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        document.getElementById('audioFileName').textContent = file.name;
    }
});