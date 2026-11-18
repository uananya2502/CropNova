# Run and deploy CropNova

CropNova is a Python web application. Its crop reasoning, fuzzy analysis and task planning run on the application server; a prepared MiniLM encoder provides local evidence search. Optional generated explanations use the configured provider. Static-only hosting cannot run this backend.

## Website flow

- `/`: introduction and entry point.
- `/assess`: field form, including explicit `?preset=reference-wheat` examples.
- `/assessment/{token}`: saved crop findings, comparisons and questions.
- `/assessment/{token}/report`: the personalised report shown directly on the website.
- `/assessment/{token}/plan`: next-step planning and unresolved questions.
- `/assessment/{token}/edit`: a prefilled form that creates a new assessment when submitted.
- `/how-it-works`, `/sources`, `/privacy`: explanatory pages.

Submitting the form returns a 303 redirect to a new saved-result URL. Refreshing, navigating between result pages and downloading the PDF reuse that snapshot. They do not rerun the assessment or call the provider again. Legacy `/?preset=...` example links redirect to `/assess?preset=...`.

## Local Python startup

Use Python 3.13, the tested runtime:

```sh
python3 -m pip install -r requirements.txt
python3 scripts/prepare_transformer.py
python3 scripts/check_deployment.py --require-model
python3 app.py
```

Open `http://127.0.0.1:8000/`. The development server loads allowed AI settings from a local, Git-ignored `.env`. Stop an existing server before starting another on that port.

## Production Python startup

Use the repository root as the working directory. A Procfile is included. The production start command is:

```sh
gunicorn --config gunicorn.conf.py app:application
```

The configuration uses the host's `PORT`, one worker and four threads. The lightweight web app is preloaded before worker forks; the encoder remains lazily loaded inside a worker. One worker shares a single loaded encoder and local SQLite database. Provider calls share two concurrency slots so they do not occupy every request thread. Private assessment URLs are not written to Gunicorn access logs by this configuration. A hosting proxy can maintain separate logs; configure those appropriately.

Configure private environment variables on the host:

```text
AI_PROVIDER=gemini
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_API_KEY=<private key>
CROPNOVA_DATA_DIR=<private writable persistent directory>
CROPNOVA_MODEL_CACHE=<prepared model-cache directory>
```

Gunicorn does not automatically read the local `.env`; hosted services must supply their environment. No API key is required for the core comparisons. Missing quota or provider failures preserve the recorded findings. No automatic paid-provider fallback is used.

The Python build step is `pip install -r requirements.txt`, followed by `python scripts/prepare_transformer.py`. On a Linux CPU host, install the pinned CPU torch wheel from `https://download.pytorch.org/whl/cpu` first, as the Dockerfile does, to avoid pulling CUDA packages. Preserve the resulting model cache in the runtime. Browser requests never initiate model downloads. The encoder requires additional memory and disk space for PyTorch and its weights; measure usage on the chosen host. Free API quota does not provide free application hosting.

## Docker setup

The Dockerfile uses Python 3.13, CPU PyTorch, a prepared model cache, a non-root application user and a readiness health check. It excludes local keys, saved assessments and generated reports from the build context.

With Docker installed:

```sh
docker compose up --build -d
```

Compose opens `http://127.0.0.1:8000/` by default and uses the named `cropnova-data` volume for saved assessments. It reads the declared optional Gemini settings through Compose interpolation; never print resolved configuration that contains a real key. To stop while preserving data, use `docker compose down` without deleting volumes.

For a public Docker host, build with the Dockerfile, provide private environment settings, attach writable persistent storage at `/data`, and configure the host's HTTPS/domain routing. The application user has UID 10001; an externally mounted data directory must be writable by that user. The model cache is included in the image and the runtime uses Hugging Face offline mode. `PORT` can be set by the host.

Docker is not installed in the current workspace environment. The container definition has been prepared and reviewed, but an image build/run is not claimed here. The production Gunicorn path is verified separately.

Implementation references: [Dockerfile reference](https://docs.docker.com/reference/dockerfile/), [Compose environment interpolation](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/), [PyTorch installation](https://pytorch.org/get-started/locally/).

## Health and checks

`GET /health` checks process liveness. `GET /ready` validates the knowledge records and tests SQLite access, returning 503 when a core component is unavailable without revealing private failure details. Neither endpoint calls a language-model service. HEAD requests return the same headers as GET without a body.

Before deployment:

```sh
python3 -m pytest -q
python3 scripts/check_deployment.py --require-model
```

A host with ephemeral storage can lose saved report links on restart. Multiple machines need shared storage and shared quota controls; the included local SQLite and in-process limits are for one application instance. Configure HTTPS through the host. Actual field use still needs independent local agricultural review; deployment does not establish agronomic accuracy.

Private result and report pages send noindex headers, and robots.txt discourages indexing. These indexing hints are not access control. Saved links expire after one hour and at most 100 reports are retained. Anyone holding a valid link can view it. Expired rows are cleaned on later saves. API keys, the database, model files and private reports must not enter a public repository.

This configuration prepares the application for hosting. It does not publish a public site, attach a domain or change a billing plan.
