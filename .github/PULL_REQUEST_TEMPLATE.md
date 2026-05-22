## Summary
<!-- What does this PR change and why? -->

## Type of change
- [ ] Bug fix
- [ ] New feature / strategy
- [ ] Indicator / signal logic update
- [ ] UI / dashboard improvement
- [ ] Dependency update
- [ ] Config / deployment change

## Testing done
- [ ] All CI jobs pass (`ci.yml`)
- [ ] Ran locally: `streamlit run app.py`
- [ ] Tested affected strategy in backtester
- [ ] Verified balance persistence works after restart

## Checklist
- [ ] No secrets or API keys committed
- [ ] `requirements.txt` updated if new dependencies added
- [ ] No hardcoded file paths (use `_get_db_path()`)
- [ ] Signals still pass RR ≥ 1.5 and confidence ≥ 60 filter
