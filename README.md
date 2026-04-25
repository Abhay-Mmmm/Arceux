# Arceux | AI-Native Security Operations Center

Arceux is a next-generation SOC dashboard designed to visualize, analyze, and remediate security threats in real-time. Built with a focus on **AI integration, aesthetic excellence, and operational speed**.

## 🚀 Key Features

- **🌐 Real-Time System Heartbeat**: Live visualization of system latency and health status across all services.
- **🤖 AI Analyst**: Integrated chatbot capable of explaining alerts, summarizing threats, and recommending remediation actions with a realistic, premium interface.
- **🛡️ CrewAI Integration**: Autonomous agents for threat hunting and log analysis.
- **⚡ Interactive Dashboard**: Fully responsive, dark-mode first design with glassmorphic elements.
- **🔔 Live Alerts**: Dynamic alert feed with contextual analysis.

## 🛠️ Technology Stack

### **Frontend**
- **Framework**: React + Vite
- **Styling**: TailwindCSS + Custom CSS Variables
- **Components**: Lucide Icons, Shadcn UI Concepts
- **Charts**: Recharts

### **Backend**
- **API**: FastAPI (Python)
- **AI Engine**: Groq (`llama-3.3-70b-versatile`) + CrewAI
- **Data**: JSON-based storage for simulation

## 📦 Project Structure

- `client/`: React frontend application
- `server/`: Python FastAPI backend and AI logic
- `artifacts/`: Project documentation, architecture guides, and implementation plans

## 🏁 Getting Started

### Prerequisites
- Node.js (v18+)
- Python (v3.10+)

### Installation

1. **Start the Backend**
   ```bash
   cd server
   # Ensure requirements are installed
   # pip install -r requirements.txt
   python main.py
   ```

2. **Start the Frontend**
   ```bash
   cd client
   npm install
   npm run dev
   ```

3. **Access the Dashboard**
   Open [http://localhost:5173](http://localhost:5173) in your browser.

---

*Crafted with precision for the future of SecOps.*
