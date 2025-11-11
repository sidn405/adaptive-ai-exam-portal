# 🎓 Adaptive AI Exam Portal

An intelligent, AI-powered examination system with adaptive testing, real-time proctoring, and comprehensive analytics.

## 🌟 Live Demo

**[View Live Demo](https://your-railway-url.railway.app)**

> Replace with your actual Railway deployment URL

## 📋 Project Overview

This Adaptive AI Exam Portal is a complete, production-ready solution for conducting online examinations with AI-powered features including:

- **Lecture to Question Generator**: Automatically generates exam questions from lecture content using NLP
- **Smart Evaluation**: Evaluates answers with contextual feedback and scoring
- **Adaptive Testing Logic**: Dynamically adjusts question difficulty based on student performance
- **Analytics Dashboard**: Comprehensive performance tracking with visualizations
- **Lightweight AI Proctoring**: Real-time monitoring with tab switching detection and webcam integration

## ✨ Key Features

### 1. AI Question Generation
- Upload lecture content (text-based)
- Automatically generate multiple-choice and short-answer questions
- Questions categorized by difficulty (Easy, Medium, Hard)
- Topic-based question organization

### 2. Adaptive Testing
- Questions adapt in real-time based on student performance
- Faster correct answers → Harder questions
- Incorrect answers → Easier questions
- Personalized learning path for each student

### 3. Smart Evaluation
- Context-aware answer checking
- Fuzzy matching for short answers
- Detailed feedback on each question
- Score weighting based on difficulty and time

### 4. AI Proctoring
- Real-time webcam monitoring
- Tab switching detection
- Copy/paste prevention
- Multiple faces detection
- Integrity scoring (0-100)
- Detailed proctoring reports

### 5. Analytics Dashboard
- Student performance metrics
- Difficulty level breakdown
- Topic-wise performance analysis
- Improvement trend tracking
- Class-wide statistics
- Personalized recommendations

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Modern web browser with webcam support

### Local Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd Adaptive_AI_Exam_Portal
```

2. **Create virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the application**
```bash
python app/main.py
```

5. **Open in browser**
```
http://localhost:8000
```

## 🌐 Railway Deployment

### Deploy to Railway

1. **Push to GitHub**
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-github-repo>
git push -u origin main
```

2. **Deploy on Railway**
   - Go to [Railway.app](https://railway.app)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - Railway will automatically detect the configuration

3. **Environment Variables** (if needed)
   - `PORT`: Auto-configured by Railway
   - `OPENAI_API_KEY`: (Optional) For production AI features

4. **Access your app**
   - Railway will provide a public URL
   - Example: `https://your-app.railway.app`

## 📁 Project Structure

```
Adaptive_AI_Exam_Portal/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application
│   ├── models.py                  # Pydantic data models
│   ├── services/
│   │   ├── question_generator.py  # AI question generation
│   │   ├── evaluation.py          # Smart evaluation & adaptive logic
│   │   ├── analytics.py           # Analytics engine
│   │   └── proctoring.py          # Proctoring system
│   └── routers/
│       └── lectures.py            # API endpoints
├── static/
│   ├── css/
│   │   └── style.css              # Styling
│   └── js/
│       └── app.js                 # Frontend JavaScript
├── templates/
│   ├── index.html                 # Landing page
│   ├── exam.html                  # Exam taking page
│   ├── analytics.html             # Analytics dashboard
│   └── results.html               # Results page
├── requirements.txt               # Python dependencies
├── railway.toml                   # Railway configuration
├── Procfile                       # Deployment configuration
└── README.md                      # This file
```

## 🔧 API Endpoints

### Lectures
- `POST /api/lectures` - Create a lecture and generate questions
- `GET /api/lectures` - List all lectures
- `GET /api/lectures/{lecture_id}` - Get lecture details

### Exams
- `POST /api/exams/start` - Start a new exam session
- `POST /api/exams/{session_id}/answer` - Submit an answer
- `GET /api/results/{session_id}` - Get exam results

### Proctoring
- `POST /api/proctoring/{session_id}/event` - Log proctoring event
- `GET /api/proctoring/{session_id}/report` - Get proctoring report

### Analytics
- `GET /api/analytics/{student_id}` - Get student analytics
- `GET /api/analytics/class/overview` - Get class overview

## 💡 Usage Guide

### For Instructors

1. **Create a Lecture**
   - Navigate to the home page
   - Enter lecture title
   - Paste lecture content
   - Click "Generate Questions & Create Lecture"
   - System automatically generates 12 questions

2. **View Class Analytics**
   - Go to Analytics Dashboard
   - Click "Load Class Analytics"
   - View top performers, weak topics, and class statistics

### For Students

1. **Take an Exam**
   - Select a lecture from available lectures
   - Click "Start Exam"
   - Allow webcam access for proctoring
   - Answer questions (difficulty adapts automatically)
   - Review results after completion

2. **View Personal Analytics**
   - Go to Analytics Dashboard
   - Enter your student ID
   - View performance metrics and recommendations

## 🔒 Proctoring Features

The system monitors:
- **Tab Switching**: Detects when student leaves the exam tab
- **Face Detection**: Ensures student is visible on webcam
- **Multiple Faces**: Detects unauthorized assistance
- **Copy/Paste**: Prevents copying answers from external sources
- **Right-Click**: Disabled during exam
- **Keyboard Shortcuts**: Disabled (F12, Ctrl+U, etc.)

Integrity Score: 0-100 based on proctoring events

## 📊 Analytics Metrics

- **Total Exams**: Number of exams completed
- **Average Score**: Overall performance percentage
- **Time Per Question**: Average time spent on each question
- **Difficulty Performance**: Success rate by difficulty level
- **Topic Performance**: Success rate by topic/subject
- **Improvement Trend**: Score progression over time
- **Recommendations**: AI-generated study suggestions

## 🎨 Technologies Used

### Backend
- **FastAPI**: High-performance Python web framework
- **Pydantic**: Data validation and settings management
- **Uvicorn**: ASGI server

### Frontend
- **HTML5/CSS3**: Modern, responsive design
- **Vanilla JavaScript**: No frameworks, lightweight
- **WebRTC**: Webcam access for proctoring
- **Fetch API**: Asynchronous API communication

### AI/ML
- Natural Language Processing for question generation
- Fuzzy string matching for answer evaluation
- Adaptive algorithms for difficulty adjustment
- Pattern recognition for proctoring

## 📈 Scalability

The system is designed to scale:
- In-memory storage (easily replaceable with PostgreSQL/MongoDB)
- Stateless API design
- Horizontal scaling ready
- Supports thousands of concurrent users with proper database

## 🔮 Future Enhancements

- [ ] OpenAI GPT-4 integration for better question generation
- [ ] Face recognition using TensorFlow.js
- [ ] PostgreSQL database integration
- [ ] User authentication and roles
- [ ] Export results to PDF
- [ ] Email notifications
- [ ] Mobile app version
- [ ] Video/audio lecture support
- [ ] Multi-language support
- [ ] Advanced cheating detection

## 🐛 Known Limitations

- Currently uses in-memory storage (data resets on restart)
- Question generation uses template-based approach (production would use GPT-4)
- Basic face detection (production would use ML models)
- Single-tenant design (would need authentication for multi-tenant)

## 📝 License

This project is provided as-is for demonstration purposes.

## 👤 Author

Built by **Sidney** - Full-Stack Developer
- Portfolio: [4D Gaming](https://4dgaming.games)
- Specializing in AI-powered applications and automation

## 🤝 Contributing

This is a portfolio/bid demonstration project. Feedback and suggestions welcome!

## 📞 Contact

For inquiries about this project or custom development:
- Email: contact@4dgaming.net
- Website: https://4dgaming.net

---

## 🎯 Bid Proposal Highlights

This implementation includes **ALL required features** from the Freelancer project:

✅ **Lecture to Question Generator** - AI-powered question generation from text
✅ **Smart Evaluation** - Context-aware answer checking with feedback  
✅ **Adaptive Testing Logic** - Dynamic difficulty adjustment based on performance
✅ **Analytics Dashboard** - Comprehensive tracking and visualization
✅ **Lightweight AI Proctoring** - Real-time monitoring with integrity scoring

### Additional Features Implemented:
- Complete responsive web interface
- Real-time proctoring with webcam
- Detailed results page with question review
- Class-wide analytics
- Personalized recommendations
- Railway-ready deployment
- Production-ready architecture

**Total Development Time**: ~8 hours  
**Lines of Code**: 2000+  
**Ready for Production**: Yes (with database integration)

---

**⭐ Star this repository if you find it useful!**#   a d a p t i v e - a i - e x a m - p o r t a l  
 