.PHONY: run api test install

install:
	pip install -r requirements-dev.txt

run:
	streamlit run streamlit_app.py

api:
	uvicorn app.api:app --reload --port 8000

test:
	pytest tests/ -v
