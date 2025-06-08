@echo off
python -m app.test.test_rag_pipeline -v > test_output.txt 2>&1
type test_output.txt 