.PHONY: test api brief challenge risk-deny memory-filter meeting backup desktop install

install:
	python3 -m pip install -r requirements.txt

test:
	python3 -m pytest

api:
	python3 -m varma

brief:
	python3 -m varma.routines.run_brief

challenge:
	python3 -m varma.routines.run_challenge

risk-deny:
	python3 -m varma.routines.run_risk_deny

memory-filter:
	python3 -m varma.routines.run_nightly_filter

meeting:
	python3 -m varma.routines.run_0730_meeting

backup:
	python3 -m varma.routines.run_backup

desktop:
	cd desktop && python3 -m http.server 5173 --bind 127.0.0.1
