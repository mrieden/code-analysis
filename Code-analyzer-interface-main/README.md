🚀 AI-Powered Code Quality Dashboard (Frontend)

This is the frontend interface for the SOLID Code Analyzer. It provides a real-time, interactive dashboard that visualizes code complexity, SOLID principle compliance, and clean code metrics using WebSockets.
✨ Features

    Real-time Analysis: Connects to a FastAPI backend via WebSockets for instant feedback as you type.

    Complexity Visualization: Visual cards for Time Complexity (O(N)) and Space Complexity (O(1) to O(N2)).

    SOLID Scorecard: Detailed breakdown of Single Responsibility, Open-Closed, Liskov Substitution, Interface Segregation, and Dependency Inversion principles.

    Clean Code Insights: Displays naming quality scores, maintainability indices (Radon), and Pylint violations.

    Interactive Editor: Syntax-highlighted code editor for testing Python snippets.

🛠️ Tech Stack

    Framework: React.js (Vite)

    Styling: Tailwind CSS / Lucide React (Icons)

    Communication: WebSockets (WS API)

    Visuals: Framer Motion (for smooth card transitions)

📥 Getting Started
1. Prerequisites

Ensure you have Node.js installed (v18 or higher recommended).
2. Installation
Bash

# Clone the repository
git clone https://github.com/your-username/code-analyzer-frontend.git

# Navigate to the directory
cd code-analyzer-frontend

# Install dependencies
npm install

3. Environment Setup

Create a .env file in the root directory and point it to your backend:
Code snippet

VITE_WS_URL=ws://localhost:8000/ws/analyze

4. Run the Development Server
Bash

npm run dev

🔌 WebSocket Data Structure

The frontend expects a JSON payload from the backend in the following format:
JSON

{
  "time_complexity": "O(n^2)",
  "space_complexity": "O(n)",
  "solid_report": {
    "S": { "status": "Pass", "reason": "..." },
    "D": { "status": "Violation", "reason": "Concrete dependency detected" }
  },
  "clean_report": {
    "naming_quality": { "naming_score": 85 },
    "radon": { "maintainability_index": 72 }
  }
}

📂 Project Structure
Plaintext

src/
├── components/       # UI Cards (SolidCard, ComplexityCard, Header)
├── hooks/            # useWebSocket logic
├── styles/           # Tailwind configuration
└── App.jsx           # Main Dashboard Layout

🤝 Contributing

    Fork the project.

    Create your Feature Branch (git checkout -b feature/AmazingFeature).

    Commit your changes (git commit -m 'Add some AmazingFeature').

    Push to the Branch (git checkout origin feature/AmazingFeature).

    Open a Pull Request.
