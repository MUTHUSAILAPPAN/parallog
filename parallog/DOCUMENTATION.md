# Parallog Documentation

Parallog analyzes application logs with a map-reduce pipeline. It supports a
single-process baseline, local multiprocessing, and HTTP workers that can run
in separate Docker containers or on separate machines.

## Contents

- [Requirements and installation](#requirements-and-installation)
- [Quick start](#quick-start)
- [Distributed system](#distributed-system)
- [Browser dashboard](#browser-dashboard)
- [Input formats and reports](#input-formats-and-reports)
- [Benchmarks](#benchmarks)
- [How the project works](#how-the-project-works)
- [Project structure](#project-structure)
- [Troubleshooting and limitations](#troubleshooting-and-limitations)

## Requirements and installation

- Python 3.8 or newer for the package.
- Docker Desktop with Docker Compose for the container-based distributed
  example. Start Docker Desktop before running the commands below.
- Flask and Requests for distributed workers and the distributed coordinator.

Run commands from the repository root, the directory containing `pyproject.toml`
and the `docker/` directory.

```powershell
python -m pip install -e .
```

Install optional features as needed:

```powershell
python -m pip install -e '.[distributed]'
python -m pip install -e '.[benchmark]'
python -m pip install -e '.[distributed,benchmark,dev]'
```

The `distributed` extra installs Flask and Requests. The `benchmark` extra
installs Matplotlib for PNG charts. The `dev` extra installs pytest.

## Quick start

Generate a deterministic sample file, then analyze it using local worker
processes:

```powershell
parallog generate-sample sample_logs.jsonl --lines 100000 --seed 7
parallog run sample_logs.jsonl --mode multiprocessing --workers 4 --top 10
```

Run the single-process baseline instead:

```powershell
parallog run sample_logs.jsonl --mode sequential
```

Save a JSON report as well as printing the table:

```powershell
parallog run sample_logs.jsonl --mode multiprocessing --workers 4 --output report.json
```

The default `run` mode is `multiprocessing`. If `--workers` is omitted, the
engine uses the machine's CPU count.

## Distributed system

The included Compose file starts three HTTP map workers. On Windows, use
PowerShell from the repository root. Keep the worker terminal open while
running the coordinator in a second terminal.

### Start the worker containers

```powershell
docker compose -f docker/docker-compose.yml up --build
```

Wait until Docker reports that all three containers are running. The host ports
map to the worker service like this:

| Worker | URL from the host |
| --- | --- |
| worker 1 | `http://localhost:5001` |
| worker 2 | `http://localhost:5002` |
| worker 3 | `http://localhost:5003` |

In another PowerShell terminal, check that each worker responds:

```powershell
Invoke-RestMethod http://localhost:5001/health
Invoke-RestMethod http://localhost:5002/health
Invoke-RestMethod http://localhost:5003/health
```

Each response should contain `status: ok`.

### Run the coordinator

The coordinator runs on the host. It reads the input file, splits it into
line-aligned chunks, posts one chunk to each worker, and reduces the returned
partial results.

```powershell
parallog generate-sample sample_logs.jsonl --lines 100000 --seed 7
parallog run sample_logs.jsonl --mode distributed --worker-urls 'http://localhost:5001,http://localhost:5002,http://localhost:5003'
```

The file path is resolved by the coordinator, so the log file must exist on the
machine running that command. Workers do not need a copy of the input file.
Each worker receives its assigned raw lines over HTTP.

Save the distributed report:

```powershell
parallog run sample_logs.jsonl --mode distributed --worker-urls 'http://localhost:5001,http://localhost:5002,http://localhost:5003' --format json --output distributed-report.json
```

### Stop the workers

Press `Ctrl+C` in the terminal running Compose. To remove the stopped
containers, run this from another terminal in the repository root:

```powershell
docker compose -f docker/docker-compose.yml down
```

### Run workers without Docker

On each worker machine, install the distributed extra and start a worker. Use a
port reachable by the coordinator and permit that port through the machine's
firewall.

```powershell
python -m pip install -e '.[distributed]'
parallog serve-worker --host 0.0.0.0 --port 5000
```

Then pass each worker's reachable address to the coordinator:

```powershell
parallog run sample_logs.jsonl --mode distributed --worker-urls 'http://worker-a:5000,http://worker-b:5000'
```

The worker service has `GET /health` and `POST /map` endpoints. The map
endpoint accepts JSON containing a `lines` list and optional `config`, and
returns a partial map result.

### Use distributed mode from the dashboard

Start the worker containers as described above. Start the local dashboard in a
separate terminal:

```powershell
parallog dashboard
```

Open `http://127.0.0.1:8000`, choose or create a sample log, select
**Distributed**, enter the comma-separated worker URLs, and run the analysis.
The dashboard defaults to the loopback interface and accepts uploaded files up
to 50 MB.

## Browser dashboard

The dashboard supports sequential, multiprocessing, and distributed execution.
To create test input without an existing log, choose a sample size in the UI
and select **Create sample log**. The generated `sample_logs.jsonl` is selected
for analysis and can also be downloaded. The dashboard includes an overview,
endpoint latency analysis, and a Map / Reduce execution view.

Start it with:

```powershell
parallog dashboard
```

The default address is `http://127.0.0.1:8000`. Choose another port with
`parallog dashboard --port 8010`. By default, the dashboard binds only to the
local machine.

## Input formats and reports

Each line is parsed independently. Supported input includes:

- **JSON Lines**, one JSON object per line. For example:

  ```json
  {"level":"ERROR","method":"GET","endpoint":"/api/orders","status":500,"response_time_ms":240}
  ```

- **Apache/Nginx Common Log Format**, optionally with a trailing response-time
  value.
- Other lines containing a recognizable `DEBUG`, `INFO`, `WARN`, `ERROR`,
  `CRITICAL`, or `FATAL` level. These contribute to the level count, but have
  no endpoint, status, or latency fields.

JSON field aliases include `severity` for `level`, `path`/`url`/`route` for
`endpoint`, `status_code`/`http_status`/`code` for `status`, and
`latency_ms`/`duration_ms`/`elapsed_ms` for `response_time_ms`. If a JSON
record has no level, its HTTP status is used to infer one.

The report includes total lines, parse errors, error rate, level and HTTP
status-class counts, top endpoints, and per-endpoint average and p50/p90/p99
latencies. Counts and averages are exact. Latency percentiles are approximate
because they are calculated from bounded reservoir samples.

Useful `run` options:

| Option | Purpose |
| --- | --- |
| `--mode sequential\|multiprocessing\|distributed` | Select execution mode. |
| `--workers N` | Local process count for multiprocessing mode. |
| `--worker-urls URLS` | Comma-separated worker addresses for distributed mode. |
| `--format table\|json\|none` | Choose terminal output format. |
| `--output PATH` | Write the report as JSON. |
| `--top N` | Number of endpoints included in the report. |

## Benchmarks

Compare sequential and local multiprocessing runs:

```powershell
parallog benchmark sample_logs.jsonl --workers-list 2,4,8 --output benchmark.json --chart benchmark.png
```

Include the distributed workers in the same benchmark:

```powershell
parallog benchmark sample_logs.jsonl --workers-list 2,4 --worker-urls 'http://localhost:5001,http://localhost:5002,http://localhost:5003' --output benchmark.json --chart benchmark.png
```

The chart option requires the `benchmark` extra. Benchmark numbers depend on
the machine, input file, worker count, and network; more workers do not
necessarily mean a faster run.

## How the project works

1. **Split:** The coordinator computes line-aligned byte ranges, so a record
   is not split between chunks.
2. **Map:** Each process or HTTP worker parses its lines and returns counts,
   endpoint summaries, and bounded latency samples.
3. **Reduce:** The coordinator merges partial results into a single summary.
4. **Report:** The reduced result is formatted as a table or JSON, including
   error rates, endpoint traffic, and latency statistics.

Sequential execution uses one mapper. Multiprocessing maps chunks in local
processes. Distributed execution maps chunks on independent worker processes
over HTTP; the coordinator still performs the split and reduce steps.

## Project structure

```text
parallog/
  parser.py                 Parse and normalize log records
  chunking.py               Create line-aligned file chunks
  mapper.py                 Map log lines to partial summaries
  reducer.py                Merge partial summaries
  stats.py                  Reservoir sampling and percentile math
  engine.py                 Sequential, multiprocessing, distributed engines
  report.py                 Human-readable and JSON report formatting
  benchmark.py              Compare engine modes and plot results
  log_generator.py          Generate synthetic JSONL logs
  cli.py                    Command-line entry point
  ui.py                     Local dashboard HTTP server and analysis API
  dashboard.html            Dashboard interface
  distributed/worker.py     HTTP map worker service
docker/
  Dockerfile.worker         Worker container image
  docker-compose.yml        Three-worker local cluster
tests/                      Unit and engine tests
examples/quickstart.py      Python API example
```

Run the tests from the repository root with:

```powershell
python -m pip install -e '.[dev]'
python -m pytest -q
```

## Troubleshooting and limitations

- **Connection refused:** Ensure Docker is running, all worker containers are
  up, and the URLs use the published host ports (`5001`, `5002`, `5003`).
  Check each `/health` endpoint before launching the coordinator.
- **Missing worker URLs:** Distributed mode requires `--worker-urls` with at
  least one reachable worker.
- **Missing optional packages:** Install `.[distributed]` for Flask and
  Requests, or `.[benchmark]` for Matplotlib charts.
- **Slow distributed run:** Workers receive raw line chunks over HTTP. For
  large files, network transfer can dominate processing time.
- **Approximate percentiles:** P50/P90/P99 are estimates from reservoir
  samples; counts and error rates remain exact.
- **Security:** The example worker uses Flask's development server and has no
  authentication or TLS. Keep it on a trusted network; do not expose it
  directly to the public internet. Use a production WSGI server and an
  authenticated, encrypted network for production deployments.