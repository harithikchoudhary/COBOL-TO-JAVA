# COBOL to Java (COBOL-TO-JAVA)

A full-stack application for converting legacy COBOL code to modern C# (.NET 8) using AI. The project consists of a React frontend and a Flask backend integrated with Azure OpenAI for code analysis and conversion.

---

## Table of Contents
- [Project Overview](#project-overview)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
  - [Backend](#backend)
  - [Frontend](#frontend)
- [Environment Variables](#environment-variables)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Project Overview

This application helps organizations modernize their legacy COBOL codebases by converting COBOL code to C# (.NET 8) with the help of AI. It extracts business and technical requirements, generates modern code, and provides a user-friendly interface for uploading, analyzing, and downloading converted code.

## Project Structure

```
COBOL-TO-JAVA/
├── Backend/
│   └── Cobol-Java-Backend/
│       └── Backend/
│           ├── app/           # Flask app (routes, logic)
│           ├── main.py        # Backend entry point
│           ├── requirements.txt
│           └── ...
├── Frontend/
│   └── cobolfrontend V2/
│       ├── src/               # React source code
│       ├── package.json
│       └── ...
└── README.md                  # (This file)
```

## Prerequisites

- **Backend:**
  - Python 3.8+
  - pip
- **Frontend:**
  - Node.js (v16+ recommended)
  - npm or yarn

## Setup Instructions

### Backend

1. Navigate to the backend directory:
   ```sh
   cd Backend/Cobol-Java-Backend/Backend
   ```
2. (Optional) Create and activate a virtual environment:
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the same directory with the following variables:
   ```env
   AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint
   AZURE_OPENAI_API_KEY=your_azure_openai_api_key
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
   ```

### Frontend

1. Open a new terminal and navigate to the frontend directory:
   ```sh
   cd Frontend/cobolfrontend V2
   ```
2. Install dependencies:
   ```sh
   npm install
   # or
   yarn install
   ```

## Environment Variables

- **Backend:**
  - `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint URL
  - `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key
  - `AZURE_OPENAI_DEPLOYMENT_NAME`: (default: `gpt-4o`)
- **Frontend:**
  - The API base URL is set in `src/config.js` as `http://localhost:8010/cobo`. Change this if your backend runs elsewhere.

## Running the Application

### Start the Backend
```sh
cd Backend/Cobol-Java-Backend/Backend
python main.py
```
- The backend will start on `http://localhost:8010` by default.

### Start the Frontend
```sh
cd Frontend/cobolfrontend V2
npm start
```
- The frontend will start on `http://localhost:3000` by default and proxy requests to the backend.

## API Endpoints

### Backend (Flask)
- **Health Check:**
  - `GET /cobo/health`
- **Analyze Requirements:**
  - `POST /cobo/analyze-requirements`
  - **Payload:** `{ sourceLanguage, targetLanguage, file_data }`
- **Convert Code:**
  - `POST /cobo/convert`
  - **Payload:** `{ sourceLanguage, targetLanguage, sourceCode, businessRequirements, technicalRequirements }`

## Usage

1. Start both backend and frontend servers as described above.
2. Open the frontend in your browser (`http://localhost:3000`).
3. Upload COBOL files, analyze requirements, and convert code to C#.
4. Download the generated code and test files.

## Troubleshooting
- Ensure both backend and frontend are running.
- Check `.env` variables for backend configuration.
- If the frontend shows "Backend connection unavailable", verify the backend is running and accessible at the configured URL.

## License

[MIT](LICENSE) 