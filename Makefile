.PHONY: test test-frontend eval

test:
	cd backend && python -m pytest -q

test-frontend:
	cd frontend && npm test

eval:
	python scripts/run_eval.py
