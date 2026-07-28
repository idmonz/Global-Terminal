# Free Data Source Setup Guide

1. Copy `.env.example` to a local `.env`.
2. Leave unused keys blank.
3. Add only keys/user-agent strings you have permission to use.
4. Start the app with `streamlit run app.py`.
5. Open Data Provider Center -> Environment to confirm configured or missing-key status.

The app loads `.env` through python-dotenv at runtime. VS Code terminal env injection is optional.
