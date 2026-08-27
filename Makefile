.PHONY: test api brief challenge risk-deny desktop install

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

desktop:
	cd desktop && python3 -m http.server 5173 --bind 127.0.0.1
