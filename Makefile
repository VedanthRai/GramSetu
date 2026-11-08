.PHONY: video edit qc test

# Rebuild everything after editing demo_assets/sentences.json (live take -> edit -> QC)
video:
	bash scripts/build_video.sh

# Re-edit the current take only (no new recording)
edit:
	python scripts/edit_demo.py && python scripts/qc_video.py

qc:
	python scripts/qc_video.py

test:
	cd backend && python -m pytest -q
