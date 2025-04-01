# Set PYTHONPATH to include project root
$env:PYTHONPATH = (Get-Location)

# Run Streamlit
streamlit run app/streamlit_app.py --server.port 8053 