# trade-ticker

Deploy a streamlit instance for displaying trade tickers for Hyperdrive pools.

## Install

```bash
uv venv --python 3.10 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## Run

1. Copy your env file

```bash
cp env-sample .env
```

2. Modify env variables.

- Set ALCHEMY_API_KEY to the appropriate key for your chosen RPC_URI.

3. Modify script

- Ensure that the env variable names match the ones you used in your `.env` file.

4. Run script

```bash
streamlit run monitor_shorts.py
```