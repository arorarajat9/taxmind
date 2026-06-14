.PHONY: setup data demo test api web dev clean

# One-time setup: Python venv + deps + frontend deps + demo data
setup:
	python3 -m venv .venv
	./.venv/bin/pip install --upgrade pip
	./.venv/bin/pip install -r requirements.txt
	cd frontend && npm install
	$(MAKE) data

# Generate the synthetic kirana demo dataset
data:
	./.venv/bin/python scripts/generate_demo_data.py

# Run the full pipeline from the CLI (no servers needed) — fastest way to see it work
demo: data
	./.venv/bin/python scripts/run_full_pipeline.py

# Run the test suite
test:
	./.venv/bin/python -m pytest backend/tests -q

# Start the API only (http://localhost:8000)
api:
	./.venv/bin/uvicorn backend.api.main:app --port 8000 --reload

# Start the frontend only (http://localhost:3000)
web:
	cd frontend && npm run dev

# Start API + frontend together (one command for the full web demo)
dev:
	./scripts/dev.sh

clean:
	rm -rf output .pytest_cache backend/**/__pycache__ frontend/.next
