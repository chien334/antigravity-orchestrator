.PHONY: install test run-server clean check-agy

install:
	@chmod +x install.sh
	@./install.sh

test:
	@PYTHONPATH="packages:packages/orchestrator:$$PYTHONPATH" python3 -m unittest discover -s tests

run-server:
	@python3 packages/orchestrator/server.py --port 8484

check-agy:
	@which agy >/dev/null 2>&1 && agy --version || echo "agy not found in PATH"

clean:
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
