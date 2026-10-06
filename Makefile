.PHONY: verify project paper render
verify:
	sh ./verify.sh
project:
	sh ./verify_project.sh
paper:
	cd ../paper && sh ./build.sh
render:
	@echo "Use paper/render_pages.py separately; rendering is not part of this integration entry." >&2
	@exit 2
