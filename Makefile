BACKEND_SERVICE := backend
DOCKER_EXEC := docker compose exec -T $(BACKEND_SERVICE)
SAMPLE_RINGO_CSV ?= /data/intermediate/ringo_csv/00011400_nav.csv
SAMPLE_QC_LOG ?= /data/intermediate/qc/00011400.qc.log
SAMPLE_STATION_ID ?= 0001
OUTPUT_ROOT ?= /data/intermediate/full_run_make
RAW_DIR ?= /data/140
NATIONAL_OUTPUT_ROOT ?= /data/intermediate/national_make
MAX_STATIONS ?=
WORKERS ?=

.PHONY: test full-pipeline sample-pipeline national-pipeline

test:
	$(DOCKER_EXEC) pytest tests -q

full-pipeline:
	$(DOCKER_EXEC) python scripts/run_full_pipeline.py $(SAMPLE_RINGO_CSV) $(SAMPLE_QC_LOG) --station-id $(SAMPLE_STATION_ID) --output-root $(OUTPUT_ROOT)

sample-pipeline: test full-pipeline

national-pipeline:
	$(DOCKER_EXEC) python scripts/run_multi_station_pipeline.py $(RAW_DIR) --output-root $(NATIONAL_OUTPUT_ROOT) $(if $(MAX_STATIONS),--max-stations $(MAX_STATIONS),) $(if $(WORKERS),--workers $(WORKERS),)
